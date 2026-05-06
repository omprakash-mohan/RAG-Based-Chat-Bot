from transformers import pipeline
import warnings

warnings.filterwarnings("ignore")

pipe = pipeline(
    "text2text-generation",
    model="google/flan-t5-base"   # 🔥 changed here
)

result = pipe(
    "Explain AI in simple terms",
    max_new_tokens=120,
    do_sample=True,
    temperature=0.7
)

print(result)
