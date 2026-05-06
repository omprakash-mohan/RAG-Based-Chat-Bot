import os
os.environ["HF_HUB_OFFLINE"] = "1"

import faiss
import numpy as np
import torch
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Models
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "google/flan-t5-base"

embedder = SentenceTransformer(EMBED_MODEL)
tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL, local_files_only=True)
model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL, local_files_only=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)


# -------------------------
# READ PDF
# -------------------------
def read_pdf(file_path):
    reader = PdfReader(file_path)
    texts = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            texts.append((i + 1, text))

    return texts


# -------------------------
# CHUNK TEXT
# -------------------------
def chunk_text(text, size=500, overlap=100):
    words = text.split()
    chunks = []

    for i in range(0, len(words), size - overlap):
        chunk = " ".join(words[i:i + size])
        chunks.append(chunk)

    return chunks


# -------------------------
# BUILD VECTOR DB
# -------------------------
class RAG:
    def __init__(self, file_path):
        pages = read_pdf(file_path)

        self.data = []

        for page_num, text in pages:
            chunks = chunk_text(text)

            for chunk in chunks:
                self.data.append({
                    "page": page_num,
                    "text": chunk
                })

        texts = [d["text"] for d in self.data]

        vectors = embedder.encode(texts, convert_to_numpy=True)
        self.index = faiss.IndexFlatL2(vectors.shape[1])
        self.index.add(vectors.astype("float32"))

    # -------------------------
    # RETRIEVE
    # -------------------------
    def search(self, query, k=5):
        q_vec = embedder.encode([query], convert_to_numpy=True)
        D, I = self.index.search(q_vec.astype("float32"), k)

        results = [self.data[i] for i in I[0]]
        return results

    # -------------------------
    # GENERATE ANSWER
    # -------------------------
    def generate(self, prompt):
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = model.generate(**inputs, max_new_tokens=150)

        return tokenizer.decode(outputs[0], skip_special_tokens=True)

    # -------------------------
    # ASK QUESTION
    # -------------------------
    def ask(self, query):
        results = self.search(query)

        context = "\n\n".join([r["text"] for r in results])

        prompt = f"""
Answer the question using the context below.
If exact answer is not present, try to infer from context.

Context:
{context}

Question:
{query}

Answer clearly:
"""

        answer = self.generate(prompt)

        return answer, results

    # -------------------------
    # SUMMARIZE
    # -------------------------
    def summarize(self):
        context = "\n".join([d["text"] for d in self.data[:10]])

        prompt = f"""
Summarize this document clearly.

{context}
"""

        return self.generate(prompt)
