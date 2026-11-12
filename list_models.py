"""Print the models each configured provider/API key can use:  python list_models.py"""
from llm import LLM, OPENAI_COMPATIBLE

llm = LLM()
for provider in dict.fromkeys(e.provider for e in llm.chain):
    if provider not in OPENAI_COMPATIBLE:
        continue
    print(f"\n== {provider} ==")
    try:
        for m in llm._client(provider).models.list():
            print("  " + m.id.replace("models/", ""))
    except Exception as e:
        print(f"  could not list models: {e}")