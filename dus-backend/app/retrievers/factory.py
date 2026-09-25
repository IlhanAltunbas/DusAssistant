import os

from .azure_search_retriever import azure_search_retriever_olustur
from .qdrant_retriever import qdrant_retriever_olustur

_RETRIEVERS = {
    "qdrant": qdrant_retriever_olustur,
    "azure_search": azure_search_retriever_olustur,
}


def get_retriever():
    store_adi = os.getenv("VECTOR_STORE", "azure_search").lower()
    try:
        olustur = _RETRIEVERS[store_adi]
    except KeyError:
        raise ValueError(
            f"Bilinmeyen VECTOR_STORE: '{store_adi}'. Geçerli seçenekler: {list(_RETRIEVERS)}"
        )
    return olustur()
