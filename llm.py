"""Multi-model LLM router.

Keeps an ordered chain of (provider, model) endpoints and switches automatically when one fails:
quota (429), overload (5xx), retired model (404), bad key (401/403), timeouts or oversized requests.
Failing endpoints are put on a cooldown, so later questions skip them instantly.
Extra backup models are discovered from each provider's own model list the first time something fails.
"""
import os
import re
import time
from dataclasses import dataclass

import requests

from config import (DEFAULT_MODELS, LLM_AUTO_DISCOVER, LLM_CHAIN, LLM_FALLBACK, LLM_MODEL,
                    LLM_PROVIDER, MAX_OUTPUT_TOKENS, OLLAMA_URL)

# provider -> (base_url, api-key env var, signup link)
OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "https://console.groq.com/keys"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY",
               "https://aistudio.google.com/apikey"),
    "openai": (None, "OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
}
PROVIDER_TPM = {"groq": 8000}                 # per-request token ceiling on the free tier
HEADROOM = {"gemini": 2000, "groq": 1000}     # extra output tokens for hidden "thinking" in reasoning models
CHARS_PER_TOKEN = 3                           # conservative (numbers/tables tokenise worse than prose)
MAX_WAIT_SECONDS = 45
MAX_RATE_RETRIES = 3
SWITCHABLE = {400, 401, 403, 404, 408, 409, 413, 422, 429, 500, 502, 503, 504}
SKIP_WORDS = ("whisper", "tts", "embed", "guard", "orpheus", "image", "audio", "live", "vision", "compound",
              "imagen", "veo", "aqa", "robotics", "computer-use", "learnlm", "gemma", "moderation")


class EmptyResponse(Exception):
    """Model returned no text (e.g. reasoning used up the token budget)."""
    status_code = 422


@dataclass(eq=False)
class Endpoint:
    provider: str
    model: str
    until: float = 0.0       # cooling down until this time
    dead: bool = False       # permanently unusable this session (bad key / model gone)
    note: str = ""

    @property
    def label(self) -> str:
        return f"{self.provider} / {self.model}"


# ---------------- helpers ----------------
def _shrink(messages: list[dict], max_chars: int) -> list[dict]:
    """Trim the middle of the largest message so the whole request fits max_chars."""
    total = sum(len(m["content"]) for m in messages)
    if total <= max_chars:
        return messages
    msgs = [dict(m) for m in messages]
    i = max(range(len(msgs)), key=lambda k: len(msgs[k]["content"]))
    text = msgs[i]["content"]
    keep = max(500, len(text) - (total - max_chars) - 40)
    tail = min(800, keep // 3)          # tail usually holds the user's question
    msgs[i]["content"] = text[:keep - tail] + "\n[...trimmed to fit token limit...]\n" + text[-tail:]
    return msgs


def _status(e: Exception):
    code = getattr(e, "status_code", None)
    if code is None:
        code = getattr(getattr(e, "response", None), "status_code", None)
    return code


def _is_connection_error(e: Exception) -> bool:
    return (type(e).__name__ in ("APIConnectionError", "APITimeoutError", "ConnectError", "ReadTimeout",
                                 "ConnectTimeout", "Timeout") or isinstance(e, requests.RequestException))


def _describe(e: Exception) -> str:
    code = _status(e)
    return f"HTTP {code}" if code else type(e).__name__


def _is_daily_quota(e: Exception) -> bool:
    return bool(re.search(r"per day|daily|\bTPD\b|\bRPD\b|PerDay", str(e), re.I))


def _wait_seconds(e: Exception, attempt: int) -> float:
    """Honour the provider's own 'retry after' hint; otherwise back off exponentially."""
    try:
        ra = e.response.headers.get("retry-after")
        if ra:
            return float(ra)
    except Exception:
        pass
    msg = str(e)
    m = re.search(r"try again in (?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", msg)
    if m and (m.group(1) or m.group(2)):
        return float(m.group(1) or 0) * 60 + float(m.group(2) or 0)
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", msg, re.I)
    if m:
        return float(m.group(1))
    return min(5 * 2 ** attempt, MAX_WAIT_SECONDS)


def _rank_models(provider: str, ids: list[str]) -> list[str]:
    """Pick sensible chat models from a provider's model list, best first."""
    chat = [i for i in ids if not any(s in i.lower() for s in SKIP_WORDS)]
    if provider == "gemini":
        flash = [i for i in chat if i.startswith("gemini") and "flash" in i]

        def score(i):
            v = re.search(r"gemini-(\d+(?:\.\d+)?)", i)
            return (not any(t in i for t in ("preview", "exp")), "lite" not in i, float(v.group(1)) if v else 0.0)
        return sorted(flash, key=score, reverse=True)
    if provider == "groq":
        prefs = ("gpt-oss-120b", "gpt-oss-20b", "llama-3.3-70b", "llama-4", "qwen", "kimi", "llama-3.1-8b")

        def idx(i):
            return next((k for k, p in enumerate(prefs) if p in i), len(prefs))
        return [i for i in sorted(chat, key=idx) if idx(i) < len(prefs)]
    return chat[:3]


def _pick_backups(provider: str, ranked: list[str]) -> list[str]:
    """Choose which discovered models to add. For Gemini, mix the newest models (often overloaded)
    with older stable ones and a lite model, which usually have more spare capacity."""
    if provider != "gemini" or len(ranked) <= 4:
        return ranked[:4]
    newest = ranked[:2]
    stable = [i for i in ranked if not any(t in i for t in ("preview", "exp"))]
    older = [i for i in stable if "lite" not in i and i not in newest][-2:]
    lite = [i for i in stable if "lite" in i][:1]
    return list(dict.fromkeys(newest + older + lite))


# ---------------- router ----------------
class LLM:
    def __init__(self):
        self.chain: list[Endpoint] = []
        self.last_used = ""
        self._clients: dict = {}
        self._discovered = False
        self._build_chain()
        if not self.chain:
            env = OPENAI_COMPATIBLE.get(LLM_PROVIDER, (None, "an API key", ""))
            raise RuntimeError(f"No usable LLM configured. Set {env[1]} in your .env file"
                               + (f" (get one at {env[2]})." if env[2] else "."))

    # ----- setup -----
    @staticmethod
    def _has_key(provider: str) -> bool:
        return provider == "ollama" or bool(os.getenv(OPENAI_COMPATIBLE[provider][1]))

    def _add(self, provider: str, model: str):
        if model and not any(e.provider == provider and e.model == model for e in self.chain):
            self.chain.append(Endpoint(provider, model))

    def _build_chain(self):
        wanted = []
        if LLM_CHAIN:
            for part in LLM_CHAIN.split(","):
                part = part.strip()
                if ":" in part:
                    p, m = part.split(":", 1)
                    wanted.append((p.strip().lower(), m.strip()))
                elif part:
                    wanted.append((part.lower(), DEFAULT_MODELS.get(part.lower(), "")))
        else:
            wanted.append((LLM_PROVIDER, LLM_MODEL))
            for p in ([LLM_FALLBACK] if LLM_FALLBACK else []) + ["groq", "gemini", "openai"]:
                wanted.append((p, DEFAULT_MODELS.get(p, "")))
        for p, m in wanted:
            if p not in OPENAI_COMPATIBLE and p != "ollama":
                print(f"[LLM] Unknown provider '{p}' ignored.")
            elif self._has_key(p):
                self._add(p, m)

    def _client(self, provider: str):
        if provider not in self._clients:
            base_url, env_var, _ = OPENAI_COMPATIBLE[provider]
            from openai import OpenAI
            # We do all retrying/switching ourselves, so the SDK itself never retries.
            self._clients[provider] = OpenAI(api_key=os.getenv(env_var), base_url=base_url,
                                             max_retries=0, timeout=90)
        return self._clients[provider]

    def _discover(self):
        """Once, when something fails: add each provider's other working chat models as backups."""
        if self._discovered:
            return
        self._discovered = True
        if LLM_CHAIN or not LLM_AUTO_DISCOVER:
            return
        for provider in dict.fromkeys(e.provider for e in self.chain):
            if provider in ("openai", "ollama"):
                continue
            try:
                ids = [m.id.replace("models/", "") for m in self._client(provider).models.list()]
            except Exception as err:
                print(f"[LLM] Could not list models for {provider}: {_describe(err)}")
                continue
            for mid in _pick_backups(provider, _rank_models(provider, ids)):
                self._add(provider, mid)
        order = {p: i for i, p in enumerate(dict.fromkeys(e.provider for e in self.chain))}
        self.chain.sort(key=lambda e: order[e.provider])      # stable: keep each provider's models together
        print("[LLM] Failover chain: " + "  ->  ".join(e.label for e in self.chain))

    # ----- routing -----
    def _next_candidate(self, tried: set):
        pool = [e for e in self.chain if not e.dead and e not in tried]
        now = time.time()
        ready = [e for e in pool if e.until <= now]
        if ready:
            return ready[0]
        return min(pool, key=lambda e: e.until) if pool else None     # all cooling: earliest recovery first

    def _penalize(self, c: Endpoint, e: Exception):
        code, now = _status(e), time.time()
        if code == 429:
            c.until = now + (3600 if _is_daily_quota(e) else min(max(_wait_seconds(e, 0), 15), 120))
            c.note = "quota reached"
        elif code in (401, 403):
            for x in self.chain:
                if x.provider == c.provider:
                    x.dead, x.note = True, "key invalid or no access"
        elif code == 404:
            c.dead, c.note = True, "model not found"
        elif code in (500, 502, 503, 504) or _is_connection_error(e):
            c.until, c.note = now + 120, "provider overloaded or unreachable"
        else:
            c.until, c.note = now + 30, _describe(e)

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1500) -> str:
        tried: set = set()
        failures: list = []
        while True:
            cand = self._next_candidate(tried)
            if cand is None:
                break
            tried.add(cand)
            others = any(not e.dead and e not in tried for e in self.chain)
            try:
                out = self._call(cand, system, messages, max_tokens, patient=not others)
                cand.until = 0.0
                self.last_used = cand.label
                if failures:
                    print(f"[LLM] Answered by {cand.label} after {len(failures)} failed attempt(s).")
                return out
            except Exception as e:
                if _status(e) not in SWITCHABLE and not _is_connection_error(e):
                    raise                                   # a real bug: don't hide it behind failover
                failures.append((cand, e))
                self._penalize(cand, e)
                print(f"[LLM] {cand.label} failed ({_describe(e)}); trying the next model.")
                self._discover()
        raise RuntimeError(self._summary(failures))

    def _summary(self, failures: list) -> str:
        if not failures:
            notes = "; ".join(f"{e.label}: {e.note}" for e in self.chain) or "no models configured"
            return f"No usable model right now ({notes}). Check your API keys in .env."
        lines = "\n".join(f"- {c.label}: {_describe(e)}" for c, e in failures)
        now = time.time()
        soon = [e.until - now for e in self.chain if not e.dead and e.until > now]
        hint = f" The soonest model recovers in about {int(min(soon))}s." if soon else ""
        return ("Every configured model is busy or unavailable right now:\n" + lines + "\n" + hint +
                " Wait a moment and retry, or add another provider key (GROQ_API_KEY, GEMINI_API_KEY) in .env.")

    # ----- one endpoint -----
    def _call(self, c: Endpoint, system: str, messages: list[dict], max_tokens: int, patient: bool) -> str:
        if c.provider == "ollama":
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": c.model, "stream": False,
                      "messages": [{"role": "system", "content": system}] + messages,
                      "options": {"temperature": 0.1, "num_predict": max_tokens}},
                timeout=300)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()

        from openai import APIStatusError
        client = self._client(c.provider)
        budget = min(max_tokens, MAX_OUTPUT_TOKENS) + HEADROOM.get(c.provider, 0)
        limit_chars = 10 ** 9
        if c.provider in PROVIDER_TPM:
            limit_chars = max(2000, (PROVIDER_TPM[c.provider] - budget - 400) * CHARS_PER_TOKEN) - len(system)
        sys_msg = {"role": "system", "content": system}
        shrinks = rate_waits = server_waits = 0
        while True:
            msgs = _shrink(messages, limit_chars)
            try:
                r = client.chat.completions.create(model=c.model, messages=[sys_msg] + msgs,
                                                   max_tokens=budget, temperature=0.1,
                                                   timeout=90 if patient else 40)
                text = (r.choices[0].message.content or "").strip()
                if not text:
                    raise EmptyResponse(f"{c.label} returned an empty answer")
                return text
            except APIStatusError as e:
                code = e.status_code
                if code == 413 and shrinks < 3:
                    shrinks += 1
                    limit_chars = int(min(limit_chars, sum(len(m["content"]) for m in msgs)) * 0.7)
                elif code == 429 and patient and rate_waits < MAX_RATE_RETRIES and not _is_daily_quota(e):
                    wait = _wait_seconds(e, rate_waits)
                    if wait > MAX_WAIT_SECONDS:
                        raise
                    rate_waits += 1
                    print(f"[LLM] {c.label} rate limited; waiting {wait:.0f}s ({rate_waits}/{MAX_RATE_RETRIES})")
                    time.sleep(wait + 1)
                elif code in (500, 502, 503, 504) and server_waits < (3 if patient else 1):
                    wait = (2, 5, 10)[server_waits]
                    server_waits += 1
                    print(f"[LLM] {c.label} overloaded (HTTP {code}); retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise

    # ----- diagnostics for the UI and scripts -----
    def status(self) -> list[dict]:
        now, rows = time.time(), []
        for e in self.chain:
            if e.dead:
                state = f"unavailable ({e.note})"
            elif e.until > now:
                state = f"cooling down {int(e.until - now)}s ({e.note})"
            else:
                state = "ready"
            rows.append({"model": e.label, "state": state})
        return rows

    def check_all(self) -> list[tuple]:
        """Send a tiny request to every model in the chain. Returns (label, ok, detail) rows."""
        self._discover()
        rows = []
        for c in list(self.chain):
            t = time.time()
            try:
                out = self._call(c, "Reply with one word.", [{"role": "user", "content": "Say OK"}], 20, patient=False)
                rows.append((c.label, True, f"{out!r} in {time.time() - t:.1f}s"))
            except Exception as e:
                rows.append((c.label, False, f"{_describe(e)}: {str(e)[:120]}"))
        return rows