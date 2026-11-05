"""RAG pipeline: load -> chunk -> embed (Gemini) -> store (ChromaDB) -> retrieve."""
import glob, os
import chromadb
from google import genai
from google.genai import types
import config


def chunk(text, size=700, overlap=120):
    """Paragraph-aware chunking with character overlap between chunks."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > size:
            chunks.append(cur)
            cur = cur[-overlap:] + "\n" + p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def embed(texts, task):
    client = genai.Client(api_key=config.API_KEY)
    out = []
    for i in range(0, len(texts), 50):
        r = client.models.embed_content(
            model=config.EMBED_MODEL, contents=texts[i:i + 50],
            config=types.EmbedContentConfig(task_type=task))
        out += [e.values for e in r.embeddings]
    return out


def _collection():
    db = chromadb.PersistentClient(path=config.CHROMA_DIR)
    return db.get_or_create_collection("regulations", metadata={"hnsw:space": "cosine"})


def ingest(reset=True):
    """Ingest every .md file in knowledge/. Returns (num_docs, num_chunks)."""
    if reset:
        db = chromadb.PersistentClient(path=config.CHROMA_DIR)
        if "regulations" in [c.name for c in db.list_collections()]:
            db.delete_collection("regulations")
    col = _collection()
    ids, docs, metas = [], [], []
    files = sorted(glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md")))
    for f in files:
        name = os.path.basename(f)
        for i, c in enumerate(chunk(open(f, encoding="utf-8").read())):
            ids.append(f"{name}-{i}"); docs.append(c); metas.append({"source": name, "chunk": i})
    col.upsert(ids=ids, documents=docs, metadatas=metas,
               embeddings=embed(docs, "RETRIEVAL_DOCUMENT"))
    return len(files), len(docs)


def is_ready():
    try:
        return _collection().count() > 0
    except Exception:
        return False


def search(query, k=4):
    """Return list of dicts {source, chunk, text, score}."""
    col = _collection()
    r = col.query(query_embeddings=embed([query], "RETRIEVAL_QUERY"), n_results=k)
    return [{"source": m["source"], "chunk": m["chunk"], "text": d, "score": round(1 - dist, 3)}
            for d, m, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])]


if __name__ == "__main__":
    print("Ingested docs/chunks:", ingest())
