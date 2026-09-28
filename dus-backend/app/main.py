import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from .guvenlik import api_anahtarini_dogrula, istek_sinirini_uygula
from .rag_motoru import GECICI_HATALAR, asistana_sor

# uvicorn'un kendi logger'ı: mesajlar container loglarına düşer.
logger = logging.getLogger("uvicorn.error")

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

# Kontroller fonksiyon çalışmadan önce, bu sırayla yapılır; reddedilen istek LLM'e hiç ulaşmaz.
# Anahtar önce: anahtarsız istekler sayaçları doldurup gerçek kullanıcıların kotasını tüketemesin.
@app.post("/ask", dependencies=[Depends(api_anahtarini_dogrula), Depends(istek_sinirini_uygula)])
async def soru_sor(istek: SoruIstegi):
    try:
        # Hem soruyu hem de geçmişi (history) iletiyoruz
        yanit = asistana_sor(soru=istek.question, gecmis=istek.history)
        # Mobil taraftaki AskResponse modelimiz {"answer": ...} bekliyor
        return {"answer": yanit}
    except GECICI_HATALAR:
        logger.warning("Geçici LLM hatası, tekrar denemeler tükendi", exc_info=True)
        return {"answer": "Şu an yoğunluk veya bağlantı sorunu yaşıyoruz, birkaç saniye sonra tekrar dener misin?"}
    except Exception:
        # Ham hata iç detay (endpoint, deployment adı vb.) içerebilir; kullanıcıya değil sadece loga yazılır.
        logger.exception("/ask isteği başarısız")
        return {"answer": "Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar dene."}

if __name__ == "__main__":
    print("FastAPI sunucusu başlatılıyor...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)