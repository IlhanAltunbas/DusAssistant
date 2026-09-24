import os

from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient


def qdrant_retriever_olustur(collection_name="periodontoloji_notlari"):
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    qdrant = Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)
    return qdrant.as_retriever(search_kwargs={"k": 5})
