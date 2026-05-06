import streamlit as st
import requests

API = "http://127.0.0.1:8000"

st.title("🤖 RAG Chatbot")

# ===== UPLOAD =====
files = st.file_uploader("Upload PDF", type=["pdf"], accept_multiple_files=True)

if st.button("Upload"):
    if files:
        try:
            payload = [
                ("files", (f.name, f.getvalue(), "application/pdf"))
                for f in files
            ]

            res = requests.post(f"{API}/upload", files=payload, timeout=120)

            st.success("Uploaded!")
            st.write(res.json())

        except Exception as e:
            st.error(f"Upload error: {e}")

# ===== ASK =====
question = st.text_input("Ask question")

if st.button("Send"):
    if question:
        try:
            res = requests.post(
                f"{API}/ask",
                json={"question": question},
                timeout=120
            )

            data = res.json()

            st.subheader("Answer")
            st.write(data["answer"])
            st.write(f"Confidence: {data['confidence']}")

        except Exception as e:
            st.error(f"Connection error: {e}")