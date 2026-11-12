"""Central configuration. Everything tunable lives here."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
# Set DATA_DIR in .env to keep the database outside synced folders (OneDrive etc.)
DATA_DIR = Path(os.getenv("DATA_DIR") or (BASE_DIR / "data"))
CHROMA_DIR = DATA_DIR / "chroma"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---- LLM ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-3.8-flash",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.1",
}
LLM_MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(LLM_PROVIDER, "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Optional automatic failover when the main provider is rate-limited (e.g. groq -> gemini)
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "").lower()
# Optional explicit failover order, e.g. "groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,gemini:gemini-3.8-flash"
LLM_CHAIN = os.getenv("LLM_CHAIN", "").strip()
# When a model fails, look up the other models each provider offers and add them to the chain (0 = off)
LLM_AUTO_DISCOVER = os.getenv("LLM_AUTO_DISCOVER", "1") != "0"

# ---- Embeddings (local & free) ----
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ---- Chunking (words ~ 0.75 tokens, so 400 words ~ 530 tokens) ----
CHUNK_WORDS = 400
CHUNK_OVERLAP_WORDS = 60

# ---- Retrieval ----
TOP_K = 6
CANDIDATES = 20
MIN_SIMILARITY = 0.25
HIGH_CONF = 0.55
MED_CONF = 0.35

# ---- Conversation / summarisation ----
# ---- Token budgets ----
# Groq free tier allows ~8,000 tokens/min per request INCLUDING the output reservation,
# so we send less context there. Other providers get roomier limits.
_SMALL = LLM_PROVIDER == "groq"
HISTORY_TURNS = 4 if _SMALL else 6
CONTEXT_WORDS = 1200 if _SMALL else 6000        # max words of retrieved text per request
MAX_OUTPUT_TOKENS = 1500 if _SMALL else 3000    # cap on requested output tokens
SUMMARY_BATCH_WORDS = 1500 if _SMALL else 3000
TPM_LIMIT = 8000 if _SMALL else 0              # hard per-request token ceiling (0 = no limit)