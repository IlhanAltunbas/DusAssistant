"""Soruların hangi yoldan cevaplanacağını seçer (ASSISTANT_MODE).

chain (varsayılan): sabit akış, soru başına bir arama (rag_motoru.py).
agent: model gerektiğinde diğer dilde de arar (ajan.py).
Geçiş eval ile karar verildikten sonra ortam değişkeniyle yapılır; kod değişmez, eski moda dönmek de öyle.
"""
import os

from . import ajan, rag_motoru
from .rag_motoru import Cevap

_MODLAR = {
    "chain": rag_motoru.cevap_uret,
    "agent": ajan.cevap_uret,
}

MOD = os.getenv("ASSISTANT_MODE", "chain").lower()
# Yanlış yazılmış bir değer sessizce varsayılana düşmesin; uygulama hiç başlamasın.
if MOD not in _MODLAR:
    raise ValueError(f"Bilinmeyen ASSISTANT_MODE: '{MOD}'. Geçerli seçenekler: {list(_MODLAR)}")


def cevap_uret(soru: str, gecmis: list | None = None, mod: str | None = None) -> Cevap:
    return _MODLAR[mod or MOD](soru, gecmis)


def asistana_sor(soru: str, gecmis: list | None = None) -> str:
    return cevap_uret(soru, gecmis).metin
