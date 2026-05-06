from sentence_transformers import SentenceTransformer

print("Downloading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("✅ Download complete!")
