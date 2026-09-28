import logging
import math
import os
import secrets
import threading
import time
from collections import deque

from dotenv import load_dotenv
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

load_dotenv()

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Uygulama anahtarı
# ---------------------------------------------------------------------------

# Mobil uygulama her isteğe bu header'ı ekler.
# auto_error=False: header eksikse FastAPI'nin kendi 403'ü yerine aşağıdaki 401 dönsün.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_BEKLENEN_ANAHTAR = os.getenv("APP_API_KEY")
if not _BEKLENEN_ANAHTAR:
    # Fail closed: anahtar tanımlanmayı unutulursa API herkese açık çalışmasın, hiç başlamasın.
    raise RuntimeError("APP_API_KEY tanımlı değil.")


def api_anahtarini_dogrula(anahtar: str | None = Security(_api_key_header)) -> None:
    # compare_digest: karşılaştırma süresi, anahtarın kaçıncı karakterde yanlış olduğunu belli etmez.
    if not anahtar or not secrets.compare_digest(anahtar.encode(), _BEKLENEN_ANAHTAR.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya eksik API anahtarı.",
        )


# ---------------------------------------------------------------------------
# İstek sınırı (rate limit)
# ---------------------------------------------------------------------------

DAKIKA = 60
GUN = 24 * 60 * 60

# Ortam değişkeniyle değiştirilebilir; canlıda yeni image gerekmez, az containerapp update yeter.
_IP_SINIRLARI = [
    (int(os.getenv("RATE_LIMIT_PER_IP_MINUTE", "5")), DAKIKA),
    (int(os.getenv("RATE_LIMIT_PER_IP_DAY", "20")), GUN),
]
# Tüm kullanıcıların toplamı: çok sayıda farklı IP'den gelen kötüye kullanıma karşı faturanın tavanı.
_GENEL_GUNLUK_SINIR = int(os.getenv("RATE_LIMIT_GLOBAL_DAY", "30"))

# Kabul edilen isteklerin zamanları (son 24 saat). Sadece kabul edilenler kaydedilir, bu yüzden
# kayıt sayısı genel günlük sınırı aşamaz; bellek sınırsız büyümez.
_ip_istekleri: dict[str, deque[float]] = {}
_genel_istekler: deque[float] = deque()
# Senkron dependency'ler FastAPI'de thread havuzunda çalışır; aynı anda gelen iki istek
# sayaçları birlikte okuyup ikisi de "sınırın altındayım" demesin diye kilit.
_kilit = threading.Lock()


def istemci_ip(request: Request) -> str:
    # Azure Container Apps'te istek önce ingress proxy'sinden geçer; request.client.host proxy'nin IP'sidir.
    # Proxy gerçek IP'yi X-Forwarded-For'un sonuna ekler. Soldaki değerleri istemci kendisi yazabilir,
    # bu yüzden en sağdaki değer alınır.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[-1].strip()
    return request.client.host if request.client else "bilinmiyor"


def _eskileri_at(zamanlar: deque[float], simdi: float) -> None:
    while zamanlar and simdi - zamanlar[0] >= GUN:
        zamanlar.popleft()


def _bekleme_suresi(zamanlar: deque[float], simdi: float, sinir: int, pencere: int) -> float | None:
    # Kayan pencere: son `pencere` saniyedeki istek sayısı sınıra ulaştıysa, yer açılması için
    # pencereden çıkması gereken isteğin çıkmasına kalan süre döner.
    penceredekiler = [t for t in zamanlar if simdi - t < pencere]
    if len(penceredekiler) >= sinir:
        return pencere - (simdi - penceredekiler[-sinir])
    return None


def istek_sinirini_uygula(request: Request) -> None:
    ip = istemci_ip(request)
    simdi = time.monotonic()  # saat ayarı değişse bile geri gitmez

    with _kilit:
        ip_zamanlari = _ip_istekleri.get(ip, deque())
        _eskileri_at(ip_zamanlari, simdi)
        _eskileri_at(_genel_istekler, simdi)

        kontroller = [(ip_zamanlari, sinir, pencere, "Çok fazla soru gönderdin.") for sinir, pencere in _IP_SINIRLARI]
        kontroller.append((_genel_istekler, _GENEL_GUNLUK_SINIR, GUN, "Günlük soru kapasitesi doldu."))

        for zamanlar, sinir, pencere, mesaj in kontroller:
            bekle = _bekleme_suresi(zamanlar, simdi, sinir, pencere)
            if bekle is not None:
                logger.warning("İstek sınırı aşıldı (%s, %d/%d sn): %s", mesaj, sinir, pencere, ip)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"{mesaj} Lütfen daha sonra tekrar dene.",
                    headers={"Retry-After": str(math.ceil(bekle))},
                )

        ip_zamanlari.append(simdi)
        _ip_istekleri[ip] = ip_zamanlari
        _genel_istekler.append(simdi)

        # 24 saattir istek atmamış IP'lerin boş kayıtlarını temizle.
        for eski_ip in [k for k, v in _ip_istekleri.items() if not v or simdi - v[-1] >= GUN]:
            del _ip_istekleri[eski_ip]
