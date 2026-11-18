# 📚 RAG Based Chat Bot

A Retrieval-Augmented Generation (RAG) chatbot that allows users to upload documents and ask questions based on their content.

The system uses:

- FastAPI (Backend)
- HTML, CSS, JavaScript (Frontend)
- FAISS Vector Database
- Sentence Transformers (Embeddings)
- Mistral 7B GGUF Local LLM
- Memory Management System
- Smart Study Tools

---

# 🚀 Features

## 📂 Multi File Upload

Supports:

- PDF
- DOCX
- TXT
- CSV
- JSON
- PPT
- PPTX
- Images (PNG, JPG, JPEG)

Users can upload multiple files simultaneously.

---

## 🤖 RAG Question Answering

Ask questions directly from uploaded documents.

Examples:

- Explain Neural Networks
- What is Deep Learning?
- Summarize Unit 3
- Give key points from page 5

---

## 📝 Smart Summarization

Generate:

- Full Summary
- Page Summary
- Key Points

---

## 🧠 Memory Management

Similar to ChatGPT memory.

Users can:

- Add Memory
- Edit Memory
- Delete Memory
- Clear Memory

Example:

```text
My team name is Orchid
```

The chatbot remembers and uses this information in future responses.

Memory stored in:

```text
backend/memory/memory.txt
```

---

## 🎓 Smart Study Tools

### Generate Questions

Automatically creates study questions from uploaded documents.

Example:

```text
What is Deep Learning?
Explain CNN architecture.
What are the applications of AI?
```

---

### Create Quiz

Generates Top 5 MCQ Questions.

Example:

```text
1. What is AI?

A) Artificial Intelligence
B) Automatic Input
C) Advanced Internet
D) None

Answer: A
```

---

## 📄 Export Notes

Export generated notes and summaries.

---

# ⚙️ Technologies Used

## Backend

- Python
- FastAPI
- Uvicorn

## Vector Search

- FAISS

## Embedding Model

```text
sentence-transformers/all-MiniLM-L6-v2
```

## LLM

```text
Mistral-7B-Instruct-v0.1.Q4_K_M.gguf
```

Loaded locally using:

```python
ctransformers
```

---

# 📦 Installation

## Clone Repository

```bash
git clone https://github.com/your-username/RAG-ChatBot.git

cd RAG-ChatBot
```
---

# 📸 Screenshots

## Main Interface

- Upload documents
- Ask questions
- View responses

## Memory System

- Save custom user preferences
- Edit/Delete memories

## Smart Tools

- Generate Questions
- Create Quiz

---

# 🔍 How RAG Works

1. User uploads documents.
2. Text is extracted.
3. Text is split into chunks.
4. Embeddings are created.
5. FAISS stores vectors.
6. Relevant chunks are retrieved.
7. Mistral generates the final answer.

```text
Document
    ↓
Embeddings
    ↓
FAISS Search
    ↓
Context Retrieval
    ↓
Mistral 7B
    ↓
Answer
```

---

# 🎯 Use Cases

- Student Study Assistant
- Notes Summarizer
- Research Assistant
- College Project
- Document Chatbot
- Knowledge Base Assistant

---



# ⭐ Future Enhancements

- Voice Input
- Voice Output
- OCR Support
- Chat History
- Authentication
- Cloud Deployment
- Multi User Memory
- Better Quiz Generation
- PDF Export Improvements

---
