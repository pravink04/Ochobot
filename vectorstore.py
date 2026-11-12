"""ChromaDB vector store with hybrid (vector + BM25) retrieval via Reciprocal Rank Fusion."""
import re
from collections import defaultdict

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from fastembed import TextEmbedding

from config import CANDIDATES, CHROMA_DIR, EMBEDDING_MODEL, TOP_K

_tok = re.compile(r"\w+")


def _meta(m) -> dict:
    """Stored metadata can come back as None/partial; always return a complete dict."""
    base = {"doc_id": "", "filename": "unknown", "page": 0, "section": "", "chunk_index": 0}
    base.update(m or {})
    return base


def _tokens(text: str) -> list[str]:
    return _tok.findall(text.lower())


class VectorStore:
    def __init__(self):
        self.embedder = TextEmbedding(f"sentence-transformers/{EMBEDDING_MODEL}")  # ONNX, no torch needed
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.col = self.client.get_or_create_collection(
            "enterprise_docs", metadata={"hnsw:space": "cosine"}
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vecs = np.array(list(self.embedder.embed(texts)), dtype="float32")
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)  # cosine-ready
        return vecs.tolist()

    # ---------- write ----------
    def add_document(self, doc_id: str, filename: str, chunks: list[dict]):
        texts = [c["text"] for c in chunks]
        embs = self._embed(texts)
        self.col.add(
            ids=[f"{doc_id}-{c['chunk_index']}" for c in chunks],
            documents=texts,
            embeddings=embs,
            metadatas=[{
                "doc_id": doc_id, "filename": filename, "page": c["page"],
                "section": c["section"], "chunk_index": c["chunk_index"],
            } for c in chunks],
        )

    def delete_document(self, doc_id: str):
        self.col.delete(where={"doc_id": doc_id})

    # ---------- read ----------
    def has_document(self, doc_id: str) -> bool:
        return len(self.col.get(where={"doc_id": doc_id}, limit=1, include=[])["ids"]) > 0

    def list_documents(self) -> list[dict]:
        res = self.col.get(include=["metadatas"])
        docs: dict[str, dict] = {}
        for m in res["metadatas"]:
            m = _meta(m)
            if not m["doc_id"]:
                continue
            d = docs.setdefault(m["doc_id"], {"doc_id": m["doc_id"], "filename": m["filename"], "chunks": 0})
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["filename"].lower())

    def get_doc_chunks(self, doc_id: str) -> list[dict]:
        res = self.col.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        items = [{**_meta(m), "id": i, "text": t} for i, t, m in zip(res["ids"], res["documents"], res["metadatas"])]
        return sorted(items, key=lambda c: c["chunk_index"])

    def search(self, query: str, k: int = TOP_K, doc_ids: list[str] | None = None) -> list[dict]:
        if doc_ids is not None and len(doc_ids) == 0:
            return []
        where = {"doc_id": {"$in": list(doc_ids)}} if doc_ids else None

        corpus = self.col.get(where=where, include=["documents", "metadatas"])
        ids, docs, metas = corpus["ids"], corpus["documents"], corpus["metadatas"]
        n = len(ids)
        if n == 0:
            return []

        by_id: dict[str, dict] = {}

        # 1) semantic search
        qemb = self._embed([query])
        v = self.col.query(
            query_embeddings=qemb, n_results=min(CANDIDATES, n), where=where,
            include=["documents", "metadatas", "distances"],
        )
        vec_rank = []
        for cid, doc, meta, dist in zip(v["ids"][0], v["documents"][0], v["metadatas"][0], v["distances"][0]):
            by_id[cid] = {**_meta(meta), "id": cid, "text": doc, "similarity": round(1 - dist, 4)}
            vec_rank.append(cid)

        # 2) keyword search (BM25) over the same filtered corpus
        bm_rank = []
        qtok = _tokens(query)
        if qtok:
            scores = BM25Okapi([_tokens(d) for d in docs]).get_scores(qtok)
            for j in sorted(range(n), key=lambda j: -scores[j])[:CANDIDATES]:
                if scores[j] <= 0:
                    break
                bm_rank.append(ids[j])
                by_id.setdefault(ids[j], {**_meta(metas[j]), "id": ids[j], "text": docs[j], "similarity": 0.0})

        # 3) Reciprocal Rank Fusion
        fused: dict[str, float] = defaultdict(float)
        for ranking in (vec_rank, bm_rank):
            for rank, cid in enumerate(ranking):
                fused[cid] += 1.0 / (60 + rank)
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        return [by_id[c] for c in top]