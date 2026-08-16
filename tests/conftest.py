import os

# Satisfies pydantic Settings at import time; tests inject mock clients and never call APIs.
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
