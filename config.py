import os
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
API_KEY = os.getenv("GEMINI_API_KEY", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
CHROMA_DIR = os.path.join(BASE, "storage", "chroma")
DB_PATH = os.path.join(BASE, "storage", "memory.db")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
CATALOG_PATH = os.path.join(BASE, "data", "catalog.json")
