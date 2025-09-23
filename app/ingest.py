# ingest.py (minimal)
from pathlib import Path
from docx import Document
from pypdf import PdfReader
import os

def load_document(file_path: str) -> str:
    """
    Load text from a document (PDF, DOCX, TXT, or MD).
    """
    ext = Path(file_path).suffix.lower()
    text = ""

    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"

    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return text.strip()


def chunk_text(text, max_tokens=500):
    sentences = text.split("\n")
    chunks, cur = [], ""
    for s in sentences:
        if len((cur+" "+s).split()) > 400:
            chunks.append(cur.strip())
            cur = s
        else:
            cur += " " + s
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def load_documents_from_folder(folder_path: str) -> dict:
    """
    Load all supported documents (PDF, DOCX, TXT, MD) from a folder.
    Returns a dict {filename: text}.
    """
    supported_exts = [".pdf", ".docx", ".txt", ".md"]
    docs = {}

    for file in Path(folder_path).glob("*"):
        if file.suffix.lower() in supported_exts:
            try:
                docs[file.name] = load_document(str(file))
            except Exception as e:
                print(f"Failed to load {file.name}: {e}")

    return docs

