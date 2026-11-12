"""Print the models your current provider/API key can use:  python list_models.py"""
from llm import LLM

llm = LLM()
print(f"Provider: {llm.provider} | configured model: {llm.model}\n")
for m in llm.client.models.list():
    print(m.id.replace("models/", ""))