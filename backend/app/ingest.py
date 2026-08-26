"""
Ingests the 6 PDFs into a persistent ChromaDB collection.

Each chunk is tagged with: source filename, reliability tier, status
(CURRENT/DEPRECATED), and account scope (general vs a specific account_id).
This metadata is what lets the doc_search tool filter and rank by
authority instead of treating every source as equally trustworthy.
"""
import os
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions

from .doc_registry import DOCUMENTS, get_doc_meta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DOCS_DIR = os.path.join(BASE_DIR, "data", "raw_docs")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_store")

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def build_index(reset: bool = True):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    embed_fn = embedding_functions.ONNXMiniLM_L6_V2()

    if reset:
        try:
            client.delete_collection("parcelpilot_docs")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name="parcelpilot_docs", embedding_function=embed_fn
    )

    ids, docs, metadatas = [], [], []
    for filename in DOCUMENTS:
        path = os.path.join(RAW_DOCS_DIR, filename)
        if not os.path.exists(path):
            print(f"WARNING: missing {filename}, skipping")
            continue
        meta = get_doc_meta(filename)
        text = extract_text(path)
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            ids.append(f"{filename}::{idx}")
            # Prepend source + status so the LLM sees authority inline with content,
            # not just in a metadata field it might ignore.
            docs.append(
                f"[SOURCE: {meta['label']} | STATUS: {meta['status']} | SCOPE: {meta['scope']}]\n{chunk}"
            )
            metadatas.append({
                "filename": filename,
                "label": meta["label"],
                "tier": meta["tier"],
                "status": meta["status"],
                "scope": meta["scope"],
            })

    if ids:
        collection.add(ids=ids, documents=docs, metadatas=metadatas)
    print(f"Indexed {len(ids)} chunks from {len(DOCUMENTS)} documents into ChromaDB at {CHROMA_DIR}")
    return collection


if __name__ == "__main__":
    build_index(reset=True)
