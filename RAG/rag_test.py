import os
from ctransformers import AutoModelForCausalLM

MODEL_PATH = r"C:\Users\asus\.cache\huggingface\hub\models--TheBloke--Mistral-7B-Instruct-v0.1-GGUF\snapshots\731a9fc8f06f5f5e2db8a0cf9d256197eb6e05d1"

print("Exists:", os.path.exists(MODEL_PATH))

llm = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    model_type="mistral"
)

print(llm("What is AI?", max_new_tokens=50))