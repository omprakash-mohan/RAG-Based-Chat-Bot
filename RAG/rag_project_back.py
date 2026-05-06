from ctransformers import AutoModelForCausalLM

print("Loading Mistral model... ⏳")

llm = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Mistral-7B-Instruct-v0.1-GGUF",
    model_file="mistral-7b-instruct-v0.1.Q4_K_M.gguf",
    model_type="mistral",
    max_new_tokens=200,
    temperature=0.3
)

print("✅ Mistral ready!")
