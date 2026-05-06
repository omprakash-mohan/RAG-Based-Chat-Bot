from transformers import pipeline

print("Downloading model... please wait ⏳")

pipe = pipeline(
    "text2text-generation",
    model="google/flan-t5-small"
)

print("✅ Model downloaded successfully!")

# Test it
result = pipe("Explain AI in simple terms")
print(result)
