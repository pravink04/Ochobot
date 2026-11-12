"""RAG engine: Q&A with citations, summarisation, comparison, action items."""
import json
import re

from config import (CONTEXT_WORDS, HIGH_CONF, HISTORY_TURNS, MED_CONF,
                    MIN_SIMILARITY, SUMMARY_BATCH_WORDS, TOP_K)

NOT_FOUND = "I couldn't find this in the selected documents."

SYSTEM_QA = f"""You are an Enterprise Knowledge Copilot that answers employee questions using company documents.

Rules:
1. Answer ONLY from the numbered context excerpts provided. Never use outside knowledge.
2. Cite every fact inline with its excerpt number, e.g. [1] or [2][3].
3. If the context does not contain the answer, reply exactly: "{NOT_FOUND}" You may add one sentence on related information that does exist.
4. If excerpts conflict (e.g. different policy versions), state the conflict and cite both sides.
5. Be concise and professional. Use bullets for lists and steps."""


def cite_label(c: dict) -> str:
    loc = f"p. {c['page']}" if c.get("page") else (c.get("section") or "")
    return f"{c['filename']}, {loc}" if loc else c["filename"]


def trim_chunks(chunks: list[dict], max_words: int) -> list[dict]:
    """Keep the best-ranked chunks that fit in a word budget (always keeps at least one)."""
    kept, used = [], 0
    for c in chunks:
        w = len(c["text"].split())
        if kept and used + w > max_words:
            break
        kept.append(c)
        used += w
    return kept


def build_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    blocks, sources = [], []
    for i, c in enumerate(chunks, 1):
        label = cite_label(c)
        blocks.append(f"[{i}] ({label})\n{c['text']}")
        sources.append({
            "id": i, "label": label, "filename": c["filename"], "page": c.get("page", 0),
            "section": c.get("section", ""), "text": c["text"], "similarity": c.get("similarity", 0.0),
        })
    return "\n\n".join(blocks), sources


def confidence_label(chunks: list[dict]) -> tuple[str, float]:
    best = max((c.get("similarity", 0.0) for c in chunks), default=0.0)
    return ("High" if best >= HIGH_CONF else "Medium" if best >= MED_CONF else "Low"), best


def parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start:end + 1])


class RAGEngine:
    def __init__(self, store, llm):
        self.store = store
        self.llm = llm

    # ---------------- Conversational Q&A ----------------
    def rewrite_query(self, history: list[dict], question: str) -> str:
        """Turn a follow-up like 'what about for contractors?' into a standalone query."""
        if not history:
            return question
        # Save an LLM call (and rate-limit budget): long questions with no reference words are standalone.
        refs = r"\b(it|its|they|them|their|this|that|these|those|he|she|also|then|about|same|more)\b"
        if len(question.split()) > 12 and not re.search(refs, question.lower()):
            return question
        convo = "\n".join(f"{m['role'].title()}: {m['content'][:500]}" for m in history[-HISTORY_TURNS:])
        prompt = (
            "Rewrite the user's latest question as a standalone search query, resolving pronouns "
            "and references using the conversation. Output ONLY the rewritten query.\n\n"
            f"Conversation:\n{convo}\n\nLatest question: {question}"
        )
        out = self.llm.complete("You rewrite questions for document search.",
                                [{"role": "user", "content": prompt}], max_tokens=120)
        return out.strip().strip('"') or question

    def answer(self, question: str, history: list[dict], doc_ids: list[str] | None) -> dict:
        standalone = self.rewrite_query(history, question)
        chunks = self.store.search(standalone, TOP_K, doc_ids)
        conf, best = confidence_label(chunks)

        if not chunks or best < MIN_SIMILARITY:
            return {"answer": NOT_FOUND + " Try selecting more documents or rephrasing your question.",
                    "sources": [], "confidence": "Low", "score": best, "query": standalone}

        chunks = trim_chunks(chunks, CONTEXT_WORDS)
        context, sources = build_context(chunks)
        messages = [{"role": m["role"], "content": m["content"][:700]} for m in history[-HISTORY_TURNS:]]
        messages.append({"role": "user",
                         "content": f"Context excerpts:\n\n{context}\n\nQuestion: {question}"})
        answer = self.llm.complete(SYSTEM_QA, messages, max_tokens=1200)

        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        for s in sources:
            s["cited"] = s["id"] in cited
        return {"answer": answer, "sources": sources, "confidence": conf,
                "score": best, "query": standalone}

    # ---------------- Summarisation (map-reduce) ----------------
    def summarize(self, doc_id: str, style: str) -> str:
        chunks = self.store.get_doc_chunks(doc_id)
        if not chunks:
            return "Document not found."
        style_prompts = {
            "Executive summary": "an executive summary: a 2-sentence overview followed by 5-7 key bullet points",
            "Detailed summary": "a detailed, well-structured summary with headings for each major topic",
            "Key rules & definitions": "a list of the key rules, limits, deadlines, responsibilities and definitions, grouped by topic",
        }
        # Batch chunks to fit comfortably in context. Overlap is trimmed implicitly by the LLM.
        batches, cur, words = [], [], 0
        for c in chunks:
            w = len(c["text"].split())
            if cur and words + w > SUMMARY_BATCH_WORDS:
                batches.append("\n".join(cur)); cur, words = [], 0
            cur.append(c["text"]); words += w
        if cur:
            batches.append("\n".join(cur))

        sys_ = "You summarise business documents faithfully. Do not add information that is not in the text."
        def summ(text, instr, max_out):
            return self.llm.complete(sys_, [{"role": "user", "content": f"{instr}\n\n{text}"}],
                                     max_tokens=max_out)

        if len(batches) == 1:
            partials_text = batches[0]
        else:  # MAP
            partials = [summ(b, f"Summarise part {i} of {len(batches)} of a document, keeping all "
                                f"important facts and numbers:", 700)
                        for i, b in enumerate(batches, 1)]
            # Hierarchical REDUCE so the final request never exceeds the token budget
            while sum(len(p.split()) for p in partials) > SUMMARY_BATCH_WORDS and len(partials) > 1:
                grouped, cur, w = [], [], 0
                for p in partials:
                    n = len(p.split())
                    if cur and w + n > SUMMARY_BATCH_WORDS:
                        grouped.append("\n\n".join(cur)); cur, w = [], 0
                    cur.append(p); w += n
                if cur:
                    grouped.append("\n\n".join(cur))
                if len(grouped) >= len(partials):
                    break  # cannot shrink further
                partials = [summ(g, "Merge these partial summaries into one concise summary, "
                                    "keeping key facts and numbers:", 700) for g in grouped]
            partials_text = "\n\n".join(partials)

        # FINAL
        return summ(partials_text, f"Produce {style_prompts[style]} from the following document content:", 1500)

    # ---------------- Cross-document comparison ----------------
    def compare(self, doc_ids: list[str], topic: str) -> dict:
        names = {d["doc_id"]: d["filename"] for d in self.store.list_documents()}
        chunks = []
        share = max(250, CONTEXT_WORDS // max(1, len(doc_ids)))  # fair share per document
        for d in doc_ids:  # retrieve separately so every document is represented
            chunks.extend(trim_chunks(self.store.search(topic, k=5, doc_ids=[d]), share))
        context, sources = build_context(chunks)
        doc_list = ", ".join(names.get(d, d) for d in doc_ids)
        prompt = f"""Compare the following documents on the topic: "{topic}".
Documents: {doc_list}

Use ONLY the numbered excerpts below and cite them like [1]. Produce markdown with these sections:
### Comparison table
A table with one row per aspect and one column per document.
### Key similarities
### Key differences
### Conflicts or gaps
Note anything one document covers that another omits, and any contradictions.
### Recommendation
Which document/version applies when, or what should be reconciled.

Excerpts:
{context}"""
        out = self.llm.complete(
            "You are a careful analyst comparing business documents. Never invent facts.",
            [{"role": "user", "content": prompt}], max_tokens=2000)
        return {"answer": out, "sources": sources}

    # ---------------- Action items & recommendations ----------------
    def action_items(self, doc_ids: list[str] | None, goal: str) -> dict:
        query = goal.strip() or "required actions responsibilities deadlines compliance obligations next steps"
        chunks = trim_chunks(self.store.search(query, k=10, doc_ids=doc_ids), CONTEXT_WORDS)
        if not chunks:
            return {"summary": "No relevant content found.", "action_items": [],
                    "recommendations": [], "risks": [], "sources": []}
        context, sources = build_context(chunks)
        situation = f"Situation / goal: {goal}" if goal.strip() else "Goal: identify what the organisation must do based on these documents."
        prompt = f"""{situation}

Using ONLY the excerpts below, produce a decision-support brief as a single JSON object with this exact schema:
{{
  "summary": "2-3 sentence situation summary",
  "action_items": [
    {{"action": "...", "owner": "role or team, or 'Unassigned'", "priority": "High|Medium|Low",
      "deadline": "date/timeframe from the documents, or 'Not specified'", "source": "[n]"}}
  ],
  "recommendations": ["..."],
  "risks": ["..."]
}}
Return JSON only, no commentary.

Excerpts:
{context}"""
        raw = self.llm.complete("You turn business documents into concrete, grounded action plans.",
                                [{"role": "user", "content": prompt}], max_tokens=2000)
        try:
            data = parse_json(raw)
        except Exception:
            data = {"summary": raw, "action_items": [], "recommendations": [], "risks": []}
        data["sources"] = sources
        return data