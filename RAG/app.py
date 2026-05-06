import streamlit as st
import os
from rag_backend import RAG

st.set_page_config(layout="wide")
st.title("🤖 RAG Based Chatbot")

if "rag" not in st.session_state:
    st.session_state.rag = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.session_state.rag = RAG(file_path)
    st.sidebar.success("File uploaded!")

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
query = st.chat_input("Ask your question")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    if st.session_state.rag:
        answer, sources = st.session_state.rag.ask(query)
    else:
        answer = "Upload a PDF first!"

    st.session_state.messages.append({"role": "assistant", "content": answer})

    with st.chat_message("assistant"):
        st.markdown(answer)

        with st.expander("Sources"):
            for i, s in enumerate(sources):
                st.write(f"Page {s['page']}")
                st.write(s["text"][:200])

# Buttons
if st.session_state.rag:
    col1, col2 = st.columns(2)

    if col1.button("Summarize"):
        summary = st.session_state.rag.summarize()
        st.write(summary)

    if col2.button("Explain"):
        summary = st.session_state.rag.summarize()
        st.write(summary)
