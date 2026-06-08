from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from rag_motoru import asistana_sor

app = FastAPI(
    title="DUS Periodontoloji Asistanı API",
    description="Kotlin Mobil Uygulaması için RAG tabanlı LLM Endpoint'i",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Mobil taraftan gelen history
class SoruIstegi(BaseModel):
    question: str # Mobil taraftaki AskRequest içindeki isimle aynı olmalı!
    history: Optional[List[str]] = []

@app.post("/ask")
async def soru_sor(istek: SoruIstegi):
    try:
        # Hem soruyu hem de geçmişi (history) iletiyoruz
        yanit = asistana_sor(soru=istek.question, gecmis=istek.history)
        # Mobil taraftaki AskResponse modelimiz {"answer": ...} bekliyor
        return {"answer": yanit} 
    except Exception as e:
        return {"answer": f"Backend hatası: {str(e)}"}

if __name__ == "__main__":
    print("FastAPI sunucusu başlatılıyor...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)