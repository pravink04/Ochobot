# Enterprise Knowledge Intelligence & Decision Copilot

A RAG-based GenAI app: upload company documents, ask questions with source citations,
summarise, compare documents, and generate action items.

## Setup
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then add your API key
streamlit run app.py
```
Pick the LLM in `.env`: `anthropic`, `openai`, or `ollama` (free/local; run `ollama pull llama3.1`).
Embeddings (`all-MiniLM-L6-v2`) run locally; the first run downloads the model (~90 MB).

## Try it
Upload `sample_docs/*.txt`, then ask: "How many annual leave days in 2024?", follow up with
"What about the carry-forward limit?", then use the Compare tab on both policies.

## Evaluate
```bash
python eval.py --index
```

## Layout
| File | Role |
|---|---|
| `config.py` | All settings |
| `ingestion.py` | PDF/DOCX/TXT/MD/XLSX parsing + chunking with page/section metadata |
| `vectorstore.py` | ChromaDB + BM25 hybrid retrieval (Reciprocal Rank Fusion) |
| `llm.py` | Claude / OpenAI / Ollama wrapper |
| `rag.py` | Q&A, query rewriting, summarise, compare, action items |
| `app.py` | Streamlit UI |
| `eval.py`, `eval_set.json` | Evaluation harness |

## Pipeline
Upload -> extract -> chunk (400 words, 60 overlap) -> embed -> Chroma.
Question -> rewrite using chat history -> hybrid search -> similarity gate
(below threshold = "not found") -> LLM answers from numbered excerpts -> citations + confidence.
