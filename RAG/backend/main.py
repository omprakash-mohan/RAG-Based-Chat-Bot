from pathlib import Path
from typing import List, Tuple
import hashlib
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.rag_engine import RAG, _friendly_general_chat

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
MEMORY_DIR = BASE_DIR / "backend" / "memory"
MEMORY_FILE = MEMORY_DIR / "memory.txt"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE.touch(exist_ok=True)

app = FastAPI(title="RAG Chat Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

CURRENT_RAG: RAG | None = None
CURRENT_SIGNATURE: str | None = None


@app.get("/")
def home():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "RAG Backend Running"}


@app.get("/script.js")
def script():
    return FileResponse(str(FRONTEND_DIR / "script.js"))


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health():
    return {"status": "ok"}


def _load_memory_items() -> List[dict]:
    if not MEMORY_FILE.exists():
        return []

    items = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        if "\t" in line:
            mem_id, text = line.split("\t", 1)
            mem_id = mem_id.strip()
            text = text.strip()
        else:
            mem_id = str(uuid.uuid4())[:8]
            text = line

        if text:
            items.append({"id": mem_id, "text": text})

    return items


def _save_memory_items(items: List[dict]) -> None:
    lines = []
    for item in items:
        text = str(item.get("text", "")).strip()
        mem_id = str(item.get("id", "")).strip() or str(uuid.uuid4())[:8]
        if text:
            lines.append(f"{mem_id}\t{text}")

    MEMORY_FILE.write_text("\n".join(lines), encoding="utf-8")


def _memory_text() -> str:
    items = _load_memory_items()
    if not items:
        return ""
    return "\n".join(f"- {item['text']}" for item in items if item.get("text"))


def _save_uploads(files: List[UploadFile]) -> Tuple[List[Tuple[str, bytes]], str]:
    uploads: List[Tuple[str, bytes]] = []
    sig_parts = []

    for file in files:
        raw = file.file.read()
        if not raw:
            continue

        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        path = UPLOAD_DIR / safe_name
        with open(path, "wb") as f:
            f.write(raw)

        uploads.append((safe_name, raw))
        sig_parts.append(f"{safe_name}:{hashlib.sha1(raw).hexdigest()}")

    signature = "|".join(sig_parts)
    return uploads, signature


def _get_rag(files: List[UploadFile]) -> RAG | None:
    global CURRENT_RAG, CURRENT_SIGNATURE

    if files:
        uploads, signature = _save_uploads(files)

        if not uploads:
            return CURRENT_RAG

        if CURRENT_RAG is not None and CURRENT_SIGNATURE == signature:
            return CURRENT_RAG

        CURRENT_RAG = RAG.from_uploads(uploads)
        CURRENT_SIGNATURE = signature
        return CURRENT_RAG

    return CURRENT_RAG


@app.post("/upload")
async def upload(files: List[UploadFile] = File(default=[])):
    try:
        rag = _get_rag(files)
        if rag is None:
            return {"status": "no files"}
        return {"status": "uploaded", "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
async def ask(
    question: str = Form(...),
    files: List[UploadFile] = File(default=[]),
):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)

        if rag is None:
            return _friendly_general_chat(question, memory_text=memory_text)

        return rag.ask(question, memory_text=memory_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize")
async def summarize(files: List[UploadFile] = File(default=[])):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)
        if rag is None:
            return _friendly_general_chat("Give me a short summary.", memory_text=memory_text)
        return rag.summarize(memory_text=memory_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/keypoints")
async def keypoints(files: List[UploadFile] = File(default=[])):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)
        if rag is None:
            return _friendly_general_chat("Give me key points.", memory_text=memory_text)
        return rag.key_points(memory_text=memory_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/page-info")
async def page_info(
    page: int = Form(default=1),
    files: List[UploadFile] = File(default=[]),
):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)
        if rag is None:
            return _friendly_general_chat("Tell me what this page contains.", memory_text=memory_text)
        return rag.page_info(memory_text=memory_text, page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain")
async def explain(files: List[UploadFile] = File(default=[])):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)
        if rag is None:
            return _friendly_general_chat("Explain this in simple words.", memory_text=memory_text)
        return rag.explain(memory_text=memory_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggest-questions")
async def suggest_questions(files: List[UploadFile] = File(default=[])):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)

        if rag is None:
            return {
                "questions": [
                    "What can you help me with?",
                    "Explain this in simple words.",
                    "What does this mean?",
                    "Can you give a quick summary?",
                    "What should I remember?",
                ]
            }

        return {"questions": rag.suggest_questions(memory_text=memory_text, count=8)}
    except Exception:
        return {"questions": []}


@app.post("/generate-quiz")
async def generate_quiz(
    count: int = Form(5),
    files: List[UploadFile] = File(default=[]),
):
    try:
        memory_text = _memory_text()
        rag = _get_rag(files)

        if rag is None:
            return {
                "quiz": (
                    "Here is your 5-question quiz:\n\n"
                    "1. What should you do first?\n"
                    "A) Upload a file\nB) Ignore the app\nC) Close the browser\nD) Sleep\n"
                    "Answer: A"
                )
            }

        return {"quiz": rag.generate_quiz(memory_text=memory_text, count=count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
def get_memory():
    return {"items": _load_memory_items()}


@app.post("/memory")
def save_memory(text: str = Form(...), memory_id: str = Form(default="")):
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Memory text cannot be empty.")

    items = _load_memory_items()

    if memory_id:
        updated = False
        for item in items:
            if item.get("id") == memory_id:
                item["text"] = text
                updated = True
                break
        if not updated:
            items.append({"id": memory_id, "text": text})
    else:
        items.append({"id": str(uuid.uuid4())[:8], "text": text})

    _save_memory_items(items)
    return {"items": items}


@app.delete("/memory/{memory_id}")
def delete_memory(memory_id: str):
    items = _load_memory_items()
    items = [item for item in items if item.get("id") != memory_id]
    _save_memory_items(items)
    return {"items": items}


@app.post("/memory/clear")
def clear_memory():
    _save_memory_items([])
    return {"items": []}


@app.post("/reset")
def reset():
    global CURRENT_RAG, CURRENT_SIGNATURE
    CURRENT_RAG = None
    CURRENT_SIGNATURE = None

    if UPLOAD_DIR.exists():
        for item in UPLOAD_DIR.iterdir():
            if item.is_file():
                item.unlink()

    return {"status": "reset"}