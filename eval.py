"""Mini evaluation harness. Index sample_docs first (via the UI or `python eval.py --index`).

Metrics: retrieval hit@k, keyword accuracy, and correct 'not found' behaviour.
Usage:  python eval.py [--index]
"""
import json
import sys
from pathlib import Path

from ingestion import ingest_file
from llm import LLM
from rag import NOT_FOUND, RAGEngine
from vectorstore import VectorStore

store = VectorStore()
if "--index" in sys.argv:
    for p in Path("sample_docs").glob("*"):
        print(p.name, ingest_file(store, p.name, p.read_bytes()))

engine = RAGEngine(store, LLM())
cases = json.loads(Path("eval_set.json").read_text())

hit = kw = nf = n_ret = n_nf = 0
for c in cases:
    r = engine.answer(c["question"], [], None)
    found_files = {s["filename"] for s in r["sources"]}
    if c["expected_doc"]:
        n_ret += 1
        ok_doc = c["expected_doc"] in found_files
        ok_kw = all(k.lower() in r["answer"].lower() for k in c["expected_keywords"])
        hit += ok_doc; kw += ok_kw
        print(f"{'PASS' if ok_doc and ok_kw else 'FAIL'} | doc={ok_doc} kw={ok_kw} | {c['question']}")
    else:
        n_nf += 1
        ok = NOT_FOUND.lower()[:25] in r["answer"].lower()
        nf += ok
        print(f"{'PASS' if ok else 'FAIL'} | not-found handling | {c['question']}")

print(f"\nRetrieval hit rate : {hit}/{n_ret}")
print(f"Keyword accuracy   : {kw}/{n_ret}")
print(f"Not-found handling : {nf}/{n_nf}")
