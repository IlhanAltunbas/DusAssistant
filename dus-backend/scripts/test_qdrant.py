import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import httpx

r = httpx.get("https://www.google.com")
print(r.status_code)

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

print("URL:", QDRANT_URL)

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
print(client.get_collections())