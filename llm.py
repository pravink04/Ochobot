"""Provider-agnostic LLM wrapper: groq | gemini | openai | ollama.

Groq, Gemini and OpenAI all speak the OpenAI chat API, so one client covers them.
Handles: oversized requests (413), unknown models (404), rate limits (429) and optional failover.
"""
import os
import re
import time

import requests

from config import (DEFAULT_MODELS, LLM_FALLBACK, LLM_MODEL, LLM_PROVIDER,
                    MAX_OUTPUT_TOKENS, OLLAMA_URL, TPM_LIMIT)

# provider -> (base_url, api-key env var, signup link)
OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "https://console.groq.com/keys"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY",
               "https://aistudio.google.com/apikey"),
    "openai": (None, "OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
}

CHARS_PER_TOKEN = 3     # conservative (English is ~4; numbers/tables/PDF text tokenise worse)
MAX_WAIT_SECONDS = 45   # longer than this -> don't sit and wait, fail or fail over instead
MAX_RATE_RETRIES = 3


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


def _is_daily_quota(err: Exception) -> bool:
    return bool(re.search(r"per day|daily|\bTPD\b|\bRPD\b|PerDay", str(err), re.I))


def _wait_seconds(err: Exception, attempt: int) -> float:
    """Honour the provider's own 'retry after' hint; otherwise back off exponentially."""
    try:
        ra = err.response.headers.get("retry-after")
        if ra:
            return float(ra)
    except Exception:
        pass
    msg = str(err)
    m = re.search(r"try again in (?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", msg)
    if m and (m.group(1) or m.group(2)):
        return float(m.group(1) or 0) * 60 + float(m.group(2) or 0)
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", msg, re.I)
    if m:
        return float(m.group(1))
    return min(5 * 2 ** attempt, MAX_WAIT_SECONDS)


class LLM:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or LLM_PROVIDER
        self.model = model or (LLM_MODEL if provider is None else DEFAULT_MODELS.get(self.provider, ""))
        self.client = None
        self._healed = False      # auto model-recovery runs at most once
        self._fallback_llm = None
        self._fallback_tried = False

        if self.provider in OPENAI_COMPATIBLE:
            base_url, env_var, link = OPENAI_COMPATIBLE[self.provider]
            key = os.getenv(env_var)
            if not key:
                raise RuntimeError(f"{env_var} is not set. Get a key at {link} and put it in your .env file.")
            from openai import OpenAI
            # We handle rate-limit waits ourselves (smarter than the SDK's short backoff)
            self.client = OpenAI(api_key=key, base_url=base_url, max_retries=1, timeout=120)
        elif self.provider != "ollama":
            raise RuntimeError(f"Unknown LLM_PROVIDER '{self.provider}'. Use groq, gemini, openai or ollama.")

    # ---------- public ----------
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1500) -> str:
        try:
            return self._complete(system, messages, max_tokens)
        except Exception as e:
            if not self._is_rate_limit(e):
                raise
            fb = self._get_fallback()
            if fb:
                print(f"[LLM] {self.provider} rate-limited; switching to fallback '{fb.provider}'.")
                return fb.complete(system, messages, max_tokens)
            raise RuntimeError(
                f"Rate limit reached on {self.provider} (free-tier quota). "
                + ("This looks like the DAILY quota: wait for it to reset or switch LLM_PROVIDER in .env. "
                   if _is_daily_quota(e) else "Wait about a minute and try again. ")
                + "Tip: set LLM_FALLBACK=gemini (or groq) in .env for automatic failover."
            ) from e

    # ---------- internals ----------
    @staticmethod
    def _is_rate_limit(e: Exception) -> bool:
        return getattr(e, "status_code", None) == 429

    def _get_fallback(self):
        if self._fallback_tried or not LLM_FALLBACK or LLM_FALLBACK == self.provider:
            return self._fallback_llm
        self._fallback_tried = True
        try:
            self._fallback_llm = LLM(provider=LLM_FALLBACK)
        except RuntimeError as err:   # e.g. fallback key missing
            print(f"[LLM] Fallback unavailable: {err}")
        return self._fallback_llm

    def _pick_model(self) -> str:
        """Called on a 404: ask the provider which models exist and choose a suitable chat model."""
        ids = [m.id.replace("models/", "") for m in self.client.models.list()]
        skip = ("whisper", "tts", "embed", "guard", "orpheus", "image", "audio", "live", "vision",
                "compound", "imagen", "veo", "aqa", "robotics", "computer-use", "learnlm", "gemma")
        chat = [i for i in ids if not any(s in i.lower() for s in skip)]
        pick = None
        if self.provider == "gemini":
            flash = [i for i in chat if i.startswith("gemini") and "flash" in i]

            def score(i):
                v = re.search(r"gemini-(\d+(?:\.\d+)?)", i)
                stable = not any(t in i for t in ("preview", "exp"))
                return (stable, "lite" not in i, float(v.group(1)) if v else 0.0)
            pick = max(flash, key=score) if flash else None
        elif self.provider == "groq":
            for pref in ("gpt-oss-120b", "gpt-oss-20b", "versatile", "instant"):
                pick = next((i for i in chat if pref in i), None)
                if pick:
                    break
        elif chat:
            pick = chat[0]
        if not pick:
            raise RuntimeError(f"Model '{self.model}' was not found and no chat model could be auto-selected. "
                               f"Available models: {ids}. Set LLM_MODEL in .env to one of these.")
        print(f"[LLM] Model '{self.model}' not found on {self.provider}; auto-selected '{pick}'. "
              f"Set LLM_MODEL={pick} in .env to make this permanent.")
        return pick

    def _complete(self, system: str, messages: list[dict], max_tokens: int) -> str:
        if self.provider in OPENAI_COMPATIBLE:
            from openai import APIStatusError
            # Gemini 2.5 and gpt-oss (Groq) are reasoning models: part of max_tokens goes to
            # internal "thinking", so give headroom or answers can come back empty/truncated.
            budget = min(max_tokens, MAX_OUTPUT_TOKENS) + {"gemini": 2000, "groq": 1000}.get(self.provider, 0)
            sys_msg = {"role": "system", "content": system}
            limit_chars = 10**9
            if self.provider == "groq" and TPM_LIMIT:
                limit_chars = max(2000, (TPM_LIMIT - budget - 400) * CHARS_PER_TOKEN) - len(system)
            shrinks = rate_waits = 0
            while True:
                msgs = _shrink(messages, limit_chars)
                try:
                    r = self.client.chat.completions.create(
                        model=self.model, messages=[sys_msg] + msgs,
                        max_tokens=budget, temperature=0.1)
                    return (r.choices[0].message.content or "").strip()
                except APIStatusError as e:
                    code = e.status_code
                    if code == 404 and not self._healed:
                        self._healed = True
                        self.model = self._pick_model()
                    elif code == 413 and shrinks < 3:
                        # "Too large": shrink to 70% of what we just sent and retry
                        shrinks += 1
                        limit_chars = int(min(limit_chars, sum(len(m["content"]) for m in msgs)) * 0.7)
                    elif code == 429 and rate_waits < MAX_RATE_RETRIES and not _is_daily_quota(e):
                        wait = _wait_seconds(e, rate_waits)
                        if wait > MAX_WAIT_SECONDS:
                            raise
                        rate_waits += 1
                        print(f"[LLM] Rate limited; waiting {wait:.0f}s (retry {rate_waits}/{MAX_RATE_RETRIES})")
                        time.sleep(wait + 1)
                    else:
                        raise

        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": self.model, "stream": False,
                  "messages": [{"role": "system", "content": system}] + messages,
                  "options": {"temperature": 0.1, "num_predict": max_tokens}},
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()