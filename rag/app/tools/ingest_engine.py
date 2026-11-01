# app/tools/ingest_engine.py

import os
import re
import requests
from typing import List

from app.db import insert_document


# =============================
# 🔥 EMBEDDING (NEW FIX)
# =============================

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def embed_text(text: str):
    res = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )
    res.raise_for_status()
    return res.json()["embedding"]


def embedding_to_pgvector_string(embedding):
    return "[" + ",".join(str(x) for x in embedding) + "]"


# =============================
# POLICY DETECTION
# =============================

def detect_policy_name(text: str):

    patterns = [
        r'([A-Z][A-Za-z\s]+Policy)',
        r'([A-Z]{2,}\s*Policy)',
        r'(Code of Conduct)',
        r'(POSH)',
        r'(Leave Policy)',
        r'(Travel Policy)',
        r'(Attendance Policy)',
        r'(Gratuity Policy)',
        r'(Loan Policy)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


# =============================
# SECTION TITLE EXTRACTION
# =============================

def detect_section_title(text: str):

    lines = text.split("\n")

    for line in lines[:5]:
        cleaned = line.strip()

        if 5 < len(cleaned) < 120:
            return cleaned

    return None


# =============================
# TXT
# =============================

def extract_text_from_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# =============================
# DOCX
# =============================

def extract_text_from_docx(path: str) -> str:

    from docx import Document

    doc = Document(path)

    return "\n".join(
        p.text for p in doc.paragraphs if p.text
    )


# =============================
# PDF
# =============================

def extract_text_from_pdf(path: str) -> str:

    import pdfplumber

    texts = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)

    return "\n".join(texts)


# =============================
# PPTX
# =============================

def extract_text_from_pptx(path: str) -> str:

    from pptx import Presentation

    prs = Presentation(path)

    texts = []

    for slide in prs.slides:
        slide_text = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                slide_text.append(shape.text)

        if slide_text:
            texts.append("\n".join(slide_text))

    return "\n\n".join(texts)


# =============================
# CHUNKING
# =============================

def split_text_into_chunks(
    text: str,
    max_chars: int = 1000,
    overlap: int = 200
) -> List[str]:

    if not text:
        return []

    text = text.replace("\r\n", "\n").strip()

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:

        end = start + max_chars
        chunk = text[start:end]

        if end < text_len:

            window_start = max(start, end - 100)

            last_newline = chunk.rfind("\n")
            last_space = chunk.rfind(" ")

            split_pos = max(last_newline, last_space)

            if split_pos > window_start - start:
                end = start + split_pos
                chunk = text[start:end]

        chunks.append(chunk.strip())

        start = end - overlap
        if start < 0:
            start = 0

        if start >= text_len:
            break

    return [c for c in chunks if c]


# =============================
# FILE TO CHUNKS
# =============================

def convert_file_to_chunks(path: str, max_chars=1000, overlap=200):

    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":
        text = extract_text_from_txt(path)
    elif ext == ".docx":
        text = extract_text_from_docx(path)
    elif ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext == ".pptx":
        text = extract_text_from_pptx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return split_text_into_chunks(text, max_chars, overlap)


# =============================
# INGEST FILE (FIXED)
# =============================

def ingest_file(client_id: str, path: str, max_chars=1000, overlap=200):

    chunks = convert_file_to_chunks(path, max_chars, overlap)

    for chunk in chunks:

        policy_name = detect_policy_name(chunk)
        section_title = detect_section_title(chunk)

        embedding = embed_text(chunk)
        embedding_str = embedding_to_pgvector_string(embedding)

        insert_document(
            client_id=client_id,
            content=chunk,
            embedding_str=embedding_str,
            policy_name=policy_name,
            section_title=section_title
        )

    return len(chunks)


# =============================
# INGEST TEXT (FIXED)
# =============================

def ingest_document(
    client_id: str,
    content: str,
    policy_name: str = None,
    section_title: str = None,
    max_chars: int = 1000,
    overlap: int = 200
):

    chunks = split_text_into_chunks(content, max_chars, overlap)

    for chunk in chunks:

        detected_policy = policy_name or detect_policy_name(chunk)
        detected_section = section_title or detect_section_title(chunk)

        embedding = embed_text(chunk)
        embedding_str = embedding_to_pgvector_string(embedding)

        insert_document(
            client_id=client_id,
            content=chunk,
            embedding_str=embedding_str,
            policy_name=detected_policy,
            section_title=detected_section
        )

    return len(chunks)