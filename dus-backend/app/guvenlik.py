import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

load_dotenv()

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
