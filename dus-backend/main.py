from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Az önce yazdığımız rag_motoru dosyasından ana fonksiyonu içe aktarıyoruz
from rag_motoru import asistana_sor

app = FastAPI(
    title="DUS Periodontoloji Asistanı API",
    description="Kotlin Mobil Uygulaması için RAG tabanlı LLM Endpoint'i",
    version="1.0.0"
)

# Güvenlik ve bağlantı ayarları (Mobil uygulamadan gelecek isteklere izin ver)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kotlin'den gelecek JSON verisinin modeli (Girdi)
class SoruIstegi(BaseModel):
    soru: str

# Mobil uygulamanın istek atacağı ana uç nokta
@app.post("/ask")
async def soru_sor(istek: SoruIstegi):
    try:
        # Kotlin'den gelen soruyu al, RAG motoruna ver, cevabı JSON olarak dön
        yanit = asistana_sor(istek.soru)
        return {"durum": "basarili", "cevap": yanit}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

# Sunucuyu başlatma komutu
if __name__ == "__main__":
    print("FastAPI sunucusu başlatılıyor...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)