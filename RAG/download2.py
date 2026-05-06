from langchain_huggingface import HuggingFaceEmbeddings

print("Downloading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("✅ Embedding model ready!")
