import io
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from ctransformers import AutoModelForCausalLM
from docx import Document
from pypdf import PdfReader
from pptx import Presentation

# Optional OCR support for images
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


MODEL_PATH = os.getenv(
    "RAG_MODEL_PATH",
    r"C:\Users\asus\.cache\huggingface\hub\models--TheBloke--Mistral-7B-Instruct-v0.1-GGUF\snapshots\731a9fc8f06f5f5e2db8a0cf9d256197eb6e05d1\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
)

if not Path(MODEL_PATH).exists():
    raise FileNotFoundError(
        f"Model not found at: {MODEL_PATH}\nSet RAG_MODEL_PATH to your local .gguf file."
    )

print("🔄 Loading LLM...")
LLM = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    model_type="mistral",
    gpu_layers=0
)
print("✅ Models ready")

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "had", "are", "was", "were",
    "been", "being", "into", "about", "over", "under", "between", "among", "your", "yours", "their",
    "they", "them", "there", "here", "what", "when", "where", "which", "who", "whom", "why", "how",
    "can", "could", "would", "should", "will", "shall", "may", "might", "must", "not", "only", "also",
    "just", "than", "then", "too", "very", "more", "most", "some", "such", "these", "those",
    "a", "an", "of", "to", "in", "on", "at", "by", "as", "is", "it", "or", "be", "we", "you",
    "i", "me", "my", "our", "us", "do", "does", "did", "done", "if", "again", "please",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9']+", str(text).lower())


def split_sentences(text: str) -> List[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip().split()) >= 3]


def split_text(text: str, size: int = 700, overlap: int = 120) -> List[str]:
    text = clean(text)
    if not text:
        return []
    step = max(1, size - overlap)
    return [text[i:i + size].strip() for i in range(0, len(text), step) if text[i:i + size].strip()]


def top_keywords(text: str, limit: int = 8) -> List[str]:
    tokens = [t for t in tokenize(text) if len(t) > 3 and t not in STOPWORDS and not t.isdigit()]
    if not tokens:
        return []
    return [word for word, _ in Counter(tokens).most_common(limit)]


def short_excerpt(text: str, words: int = 18) -> str:
    tokens = clean(text).split()
    if len(tokens) <= words:
        return clean(text)
    return " ".join(tokens[:words]) + "..."


def _safe_extract_from_pptx(raw: bytes) -> str:
    prs = Presentation(io.BytesIO(raw))
    parts = []
    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_text = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                slide_text.append(shape.text)
        if slide_text:
            parts.append(f"Slide {slide_idx}: " + " ".join(slide_text))
    return "\n".join(parts)


def _convert_ppt_to_pptx_and_extract(raw: bytes) -> str:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return ""

    with tempfile.TemporaryDirectory() as tmpdir:
        ppt_path = Path(tmpdir) / "input.ppt"
        out_dir = Path(tmpdir) / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        ppt_path.write_bytes(raw)

        try:
            subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "pptx",
                    "--outdir",
                    str(out_dir),
                    str(ppt_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception:
            return ""

        pptx_files = list(out_dir.glob("*.pptx"))
        if not pptx_files:
            return ""

        return _safe_extract_from_pptx(pptx_files[0].read_bytes())


def _extract_text_from_upload(filename: str, raw: bytes) -> List[Tuple[Optional[int], str]]:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        page_texts = []
        for page_no, page in enumerate(reader.pages, start=1):
            text = clean(page.extract_text() or "")
            if text:
                page_texts.append((page_no, text))
        return page_texts

    if ext == ".docx":
        doc = Document(io.BytesIO(raw))
        text = clean("\n".join(p.text for p in doc.paragraphs))
        return [(None, text)] if text else []

    if ext in {".txt", ".md", ".csv", ".json", ".html", ".htm"}:
        text = raw.decode("utf-8", errors="ignore")
        if ext in {".html", ".htm"}:
            try:
                from bs4 import BeautifulSoup
                text = BeautifulSoup(text, "html.parser").get_text(" ")
            except Exception:
                pass
        text = clean(text)
        return [(None, text)] if text else []

    if ext in {".xlsx", ".xls"}:
        try:
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None)
            parts = []
            for sheet_name, df in sheets.items():
                parts.append(f"Sheet: {sheet_name}")
                parts.append(df.astype(str).to_string(index=False))
            text = clean("\n".join(parts))
            return [(None, text)] if text else []
        except Exception:
            return []

    if ext == ".pptx":
        try:
            text = clean(_safe_extract_from_pptx(raw))
            return [(None, text)] if text else []
        except Exception:
            return []

    if ext == ".ppt":
        try:
            text = clean(_convert_ppt_to_pptx_and_extract(raw))
            return [(None, text)] if text else []
        except Exception:
            return []

    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        if OCR_AVAILABLE:
            try:
                image = Image.open(io.BytesIO(raw))
                text = clean(pytesseract.image_to_string(image))
                return [(None, text)] if text else []
            except Exception:
                return []
        return []

    return []


def clean_output(text: str) -> str:
    text = str(text or "")
    text = text.replace("<s>", "").replace("</s>", "")
    text = text.replace("[INST]", "").replace("[/INST]", "")
    text = text.replace("Answer:", "").strip()
    text = re.sub(r"[^\w\s.,!?;:()\-/'\n]", "", text)

    lines = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        key = re.sub(r"\s+", " ", line.lower())
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\b(\w+)(?:\s+\1\b){2,}", r"\1", text, flags=re.IGNORECASE)
    return text.strip()


def _looks_bad(text: str) -> bool:
    text = clean(text)
    if not text:
        return True
    if len(text.split()) < 3:
        return True
    if re.fullmatch(r"[\d\.\s\-_,]+", text):
        return True
    if re.search(r"(.)\1{5,}", text):
        return True
    if re.search(r"(?:\b\d+\.\s*){3,}", text):
        return True
    return False


def _memory_lines(memory_text: str) -> List[str]:
    lines = []
    for raw_line in str(memory_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\d\.\)\(]+\s*", "", line).strip()
        if line:
            lines.append(line)
    return lines


def _select_relevant_memory(question: str, memory_text: str, limit: int = 4) -> str:
    lines = _memory_lines(memory_text)
    if not lines:
        return ""

    q_lower = clean(question).lower()
    if any(phrase in q_lower for phrase in ["about me", "describe me", "who am i", "what do you know about me", "my memory"]):
        return "\n".join(lines[:limit])

    q_tokens = set(t for t in tokenize(question) if len(t) > 2 and t not in STOPWORDS)
    preference_keywords = {
        "language", "german", "english", "tone", "style", "remember", "always", "answer", "reply",
        "document", "summarize", "summary", "study", "notes", "prefer", "preference"
    }

    scored = []
    for line in lines:
        line_lower = line.lower()
        l_tokens = set(t for t in tokenize(line) if len(t) > 2 and t not in STOPWORDS)
        overlap = len(q_tokens & l_tokens)
        pref = sum(1 for key in preference_keywords if key in line_lower)
        score = overlap + (0.75 * pref)

        if score > 0:
            scored.append((score, line))
        elif any(key in line_lower for key in preference_keywords):
            scored.append((0.25, line))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return "\n".join(line for _, line in scored[:limit])

    return "\n".join(lines[:limit])


def _friendly_general_chat(question: str, memory_text: str = "") -> dict:
    memory_context = _select_relevant_memory(question, memory_text, limit=4)
    prompt = f"""
[INST]
You are a friendly assistant. Reply naturally like a helpful human.

If the user memory below contains a language preference or style preference, follow it.
Use the memory only if it is relevant.
Do not mention "Based on memory" or repeat the memory text verbatim.
Keep the answer complete, calm, and short.

User memory:
{memory_context if memory_context else "None"}

User question:
{question}

Answer:
[/INST]
""".strip()

    try:
        response = LLM(
            prompt,
            max_new_tokens=120,
            temperature=0.35,
            top_p=0.9,
            repetition_penalty=1.12,
        )
        answer = clean_output(response)
    except Exception:
        answer = ""

    if _looks_bad(answer):
        q_lower = clean(question).lower()
        if q_lower in {"hi", "hello", "hey"}:
            answer = "Hey there! 👋 I am ready to help."
        elif "what is hi" in q_lower or "meaning of hi" in q_lower:
            answer = "‘Hi’ is a friendly greeting. It means hello."
        else:
            answer = "Sure — ask me about your document, or say hi and I will help you naturally."

    return {
        "answer": answer,
        "confidence": 1.0,
        "sources": [],
    }


def _safe_no_text_response() -> dict:
    return {
        "answer": "I could not read useful text from that file. Please upload a readable PDF, DOCX, TXT, CSV, JSON, Excel, PowerPoint, or an image with readable text.",
        "confidence": 0.0,
        "sources": [],
    }


def _fallback_doc_answer(kind: str, context: str, page: int = 0) -> str:
    sentences = split_sentences(context)
    excerpt = sentences[:3] if sentences else [short_excerpt(context, 24)]

    if kind == "summary":
        if not excerpt:
            return "I could not find enough text to summarize."
        return "Here is a short summary:\n" + "\n".join(f"- {s}" for s in excerpt)

    if kind == "keypoints":
        if not excerpt:
            return "Key points could not be extracted from the document."
        return "Key points:\n" + "\n".join(f"- {s}" for s in excerpt)

    if kind == "page":
        if not excerpt:
            if page > 0:
                return f"I could not find page {page} in the uploaded document."
            return "I could not read enough text from that page."
        prefix = f"Page {page} information:" if page > 0 else "Page information:"
        return prefix + "\n" + "\n".join(f"- {s}" for s in excerpt)

    if kind == "explain":
        if not excerpt:
            return "I could not explain the document because the text is too short."
        return "In simple words:\n" + "\n".join(f"- {s}" for s in excerpt)

    if kind == "quiz":
        if not excerpt:
            return "1. What is the main topic of the document?\nAnswer: The document content could not be read clearly."
        return "1. What is the main topic of the document?\nAnswer: " + short_excerpt(excerpt[0], 16)

    if not excerpt:
        return "I could not find that in the uploaded document. Try a different wording or a specific page number."
    return "I found this in the document:\n" + "\n".join(f"- {s}" for s in excerpt)


@dataclass
class ChunkRecord:
    source: str
    page: Optional[int]
    text: str


class RAG:
    def __init__(self, records: List[ChunkRecord]):
        if not records:
            records = [ChunkRecord(source="__empty__", page=None, text="No readable content found.")]
        self.records = records

    @classmethod
    def from_uploads(cls, uploads: List[Tuple[str, bytes]]):
        records: List[ChunkRecord] = []

        for filename, raw in uploads:
            try:
                pages = _extract_text_from_upload(filename, raw)
                for page_no, page_text in pages:
                    for chunk in split_text(page_text):
                        if chunk.strip():
                            records.append(
                                ChunkRecord(
                                    source=filename,
                                    page=page_no,
                                    text=chunk,
                                )
                            )
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")

        return cls(records)

    def _retrieve(self, query: str, k: int = 4) -> List[dict]:
        query_tokens = [t for t in tokenize(query) if len(t) > 2 and t not in STOPWORDS]
        if not query_tokens:
            query_tokens = tokenize(query)

        ranked = []
        for idx, rec in enumerate(self.records):
            text_lower = rec.text.lower()
            rec_tokens = set(t for t in tokenize(rec.text) if len(t) > 2 and t not in STOPWORDS)
            overlap = len(set(query_tokens) & rec_tokens)
            phrase_bonus = sum(1 for term in query_tokens if term in text_lower)
            score = (2 * overlap) + phrase_bonus

            if rec.page is not None and str(rec.page) in query.lower():
                score += 1.5

            ranked.append((score, idx, rec))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top = ranked[:max(1, min(k, len(ranked)))]

        results = []
        for score, _, rec in top:
            results.append(
                {
                    "source": rec.source,
                    "page": rec.page,
                    "text": rec.text,
                    "score": float(score),
                }
            )
        return results

    def _retrieve_by_page(self, page: int, k: int = 4) -> List[dict]:
        page_records = [r for r in self.records if r.page == page]
        if not page_records:
            return []

        ranked = []
        for idx, rec in enumerate(page_records):
            overlap = len(set(tokenize(rec.text)) & set(tokenize("page content")))
            ranked.append((overlap, idx, rec))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top = ranked[:max(1, min(k, len(ranked)))]

        results = []
        for score, _, rec in top:
            results.append(
                {
                    "source": rec.source,
                    "page": rec.page,
                    "text": rec.text,
                    "score": float(score),
                }
            )
        return results

    def _build_context(self, retrieved, max_chars=1000):
        context = ""
        for item in retrieved:
            chunk = item["text"][:300]
            if len(context) + len(chunk) > max_chars:
                break
            context += chunk + "\n"
        return context.strip()

    def _generate(self, prompt: str, max_new_tokens: int = 120, temperature: float = 0.25) -> str:
        try:
            output = LLM(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
                repetition_penalty=1.12,
            )
            return clean_output(output)
        except Exception:
            return ""

    def _answer(self, query: str, instruction: str, memory_text: str = "", max_new_tokens: int = 180, page: int = 0, fallback_kind: str = "qa") -> dict:
        if self.records and self.records[0].source == "__empty__":
            return _safe_no_text_response()

        if page and page > 0:
            retrieved = self._retrieve_by_page(page, k=4)
            if not retrieved:
                return {
                    "answer": f"I could not find page {page} in the uploaded document.",
                    "confidence": 0.0,
                    "sources": [],
                }
        else:
            retrieved = self._retrieve(query, k=4)

        confidence = retrieved[0]["score"] if retrieved else 0.0
        context = self._build_context(retrieved)

        if not context.strip():
            return _safe_no_text_response()

        relevant_memory = _select_relevant_memory(query, memory_text, limit=4)
        prompt = f"""
[INST]
You are a friendly, helpful document assistant.

{instruction}

Use ONLY the document context below.
- Answer in complete sentences.
- Avoid fragments, repeated words, and garbled text.
- If the answer is not in the context, say exactly: Not found in document.
- Keep it concise and clear.

User memory (only if relevant):
{relevant_memory if relevant_memory else "None"}

Context:
{context}

Question:
{query}

Answer:
[/INST]
""".strip()

        answer = self._generate(prompt, max_new_tokens=max_new_tokens, temperature=0.25)

        if _looks_bad(answer):
            answer = _fallback_doc_answer(fallback_kind, context, page=page)

        return {
            "answer": answer,
            "confidence": round(float(confidence), 2),
            "sources": retrieved,
        }

    def ask(self, question: str, memory_text: str = "") -> dict:
        q = (question or "").strip()
        if not q:
            return {"answer": "Please type a question.", "confidence": 0.0, "sources": []}

        q_lower = q.lower()

        if q_lower in {"hi", "hello", "hey"} or "what is hi" in q_lower or "meaning of hi" in q_lower:
            return _friendly_general_chat(question, memory_text=memory_text)

        if self.records and self.records[0].source == "__empty__":
            return _friendly_general_chat(question, memory_text=memory_text)

        result = self._answer(
            query=q,
            instruction="Answer the user's question using the document context.",
            memory_text=memory_text,
            max_new_tokens=180,
            fallback_kind="qa"
        )

        if result["confidence"] < 1:
            answer_text = clean(result.get("answer", ""))
            if not answer_text:
                result["answer"] = "I couldn't find that in the uploaded document. Try asking with a different wording or a page number."

        return result

    def summarize(self, memory_text: str = "") -> dict:
        if self.records and self.records[0].source == "__empty__":
            return _safe_no_text_response()

        text = " ".join(record.text for record in self.records[:5])[:1200]
        if not text.strip():
            return _safe_no_text_response()

        prompt = f"""
Summarize the following content clearly in 3 to 5 bullet points:

{text}
""".strip()

        try:
            answer = self._generate(prompt, max_new_tokens=120, temperature=0.2)
            if _looks_bad(answer):
                answer = _fallback_doc_answer("summary", text)
            return {
                "answer": answer,
                "confidence": 1.0,
                "sources": [
                    {
                        "source": record.source,
                        "page": record.page,
                        "text": record.text,
                        "score": 0.0,
                    }
                    for record in self.records[:5]
                ],
            }
        except Exception as e:
            return {"answer": f"Error during summarization: {str(e)}", "confidence": 0.0, "sources": []}

    def key_points(self, memory_text: str = "") -> dict:
        return self._answer(
            query="Give the key points from the uploaded document.",
            instruction="Return 3 to 5 concise bullet points with the most important ideas.",
            memory_text=memory_text,
            max_new_tokens=140,
            fallback_kind="keypoints"
        )

    def page_info(self, memory_text: str = "", page: int = 0) -> dict:
        if self.records and self.records[0].source == "__empty__":
            return _safe_no_text_response()

        if page and page > 0:
            page_records = [record for record in self.records if record.page == page]
            if not page_records:
                return {
                    "answer": f"No content found for page {page}",
                    "confidence": 0.0,
                    "sources": [],
                }
            text = "\n".join(record.text for record in page_records[:3])[:800]
        else:
            page_records = self.records[:3]
            text = "\n".join(record.text for record in page_records)[:800]

        if not text.strip():
            return _safe_no_text_response()

        prompt = f"""
Explain this page content clearly in 3 short bullet points:

{text}
""".strip()

        try:
            answer = self._generate(prompt, max_new_tokens=120, temperature=0.2)
            if _looks_bad(answer):
                answer = _fallback_doc_answer("page", text, page=page)
            return {
                "answer": answer,
                "confidence": 1.0,
                "sources": [
                    {
                        "source": record.source,
                        "page": record.page,
                        "text": record.text,
                        "score": 0.0,
                    }
                    for record in page_records
                ],
            }
        except Exception as e:
            return {"answer": f"Error: {str(e)}", "confidence": 0.0, "sources": []}

    def explain(self, memory_text: str = "") -> dict:
        return self._answer(
            query="Explain the uploaded document in simple words.",
            instruction="Explain the document in a simple, friendly way that a beginner can understand.",
            memory_text=memory_text,
            max_new_tokens=160,
            fallback_kind="explain"
        )

    def suggest_questions(self, memory_text: str = "", count: int = 8) -> List[str]:
        count = max(1, min(8, int(count or 8)))

        if self.records and self.records[0].source == "__empty__":
            return [
                "What is this document about?",
                "Can you summarize it simply?",
                "What are the key points?",
                "Which topic is most important?",
                "What should I remember from it?",
                "Can you explain it in easy words?",
                "What is the conclusion?",
                "What is one important detail?",
            ][:count]

        text = " ".join(record.text for record in self.records[:6])
        keywords = top_keywords(text, limit=10)
        sentences = split_sentences(text)

        questions = []
        for kw in keywords:
            questions.append(f"What does the document say about {kw}?")
            questions.append(f"Can you explain {kw} in simple words?")

        for sent in sentences[:6]:
            important = top_keywords(sent, limit=1)
            if important:
                kw = important[0]
                questions.append(f"Why is {kw} important in the document?")
            else:
                questions.append("What is the main idea of this part?")

        if not questions:
            questions = [
                "What is the main topic?",
                "What are the key points?",
                "Can you explain it simply?",
                "What is the conclusion?",
            ]

        unique = []
        for q in questions:
            if q not in unique:
                unique.append(q)

        return unique[:count]

    def generate_quiz(self, memory_text: str = "", count: int = 5) -> str:
        count = max(1, min(5, int(count or 5)))

        if self.records and self.records[0].source == "__empty__":
            return (
                "Here is your 5-question quiz:\n\n"
                "1. What kind of file should be uploaded?\n"
                "A) Any file\nB) Readable document\nC) Music file\nD) Video file\n"
                "Answer: B\n\n"
                "2. What happens when the document is readable?\n"
                "A) The bot can answer questions\nB) The bot deletes the file\nC) The bot ignores it\nD) The bot freezes\n"
                "Answer: A\n\n"
                "3. What is the best way to ask?\n"
                "A) Ask one clear question\nB) Type random words\nC) Use only numbers\nD) Leave it blank\n"
                "Answer: A\n\n"
                "4. What should you do if the answer is not found?\n"
                "A) Rephrase the question\nB) Close the app\nC) Turn off the browser\nD) Delete the model\n"
                "Answer: A\n\n"
                "5. What can the memory panel do?\n"
                "A) Save preferences\nB) Draw pictures\nC) Download videos\nD) Format PDFs\n"
                "Answer: A"
            )

        text = " ".join(record.text for record in self.records[:6])
        keywords = top_keywords(text, limit=10)
        sentences = split_sentences(text)

        if not keywords:
            keywords = ["document", "topic", "content", "idea", "conclusion"]

        if not sentences:
            sentences = [text[:80] if text else "document content"]

        lines = ["Here is your 5-question quiz:"]
        letters = ["A", "B", "C", "D"]

        for i in range(count):
            kw = keywords[i % len(keywords)].title()
            correct = short_excerpt(sentences[i % len(sentences)], 10)
            if not correct:
                correct = kw

            distractors = [
                f"Not related to {kw}",
                f"A different idea from {kw}",
                f"An opposite concept to {kw}",
                f"General background only",
            ]

            correct_pos = i % 4
            options = []
            di = 0
            for pos in range(4):
                if pos == correct_pos:
                    options.append(correct)
                else:
                    options.append(distractors[di])
                    di += 1

            lines.append(f"{i + 1}. What is the document saying about {kw}?")
            for letter, option in zip(letters, options):
                lines.append(f"{letter}) {option}")
            lines.append(f"Answer: {letters[correct_pos]}")
            lines.append("")

        return "\n".join(lines).strip()