import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.retrievers.azure_search_retriever import azure_search_embeddings, index_adi, index_semasi

load_dotenv()

KAYNAK_KLASORU = Path(__file__).resolve().parent.parent / "kaynaklar"
QDRANT_COLLECTION = "periodontoloji_notlari"


def pdfleri_parcala(klasor: Path):
    pdf_dosyalari = sorted(klasor.glob("*.pdf"))
    if not pdf_dosyalari:
        raise SystemExit(f"Hata: '{klasor}' klasöründe hiç PDF dosyası bulunamadı!")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )

    parcalar = []
    for pdf in pdf_dosyalari:
        print(f"---> İşleniyor: {pdf.name}")
        sayfa_parcalari = text_splitter.split_documents(PyPDFLoader(str(pdf)).load())
        print(f"     {len(sayfa_parcalari)} parça")
        parcalar.extend(sayfa_parcalari)
    return parcalar


def qdranta_yukle(parcalar):
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

    # Koleksiyon varsa silinir, çift veri oluşmasın.
    if client.collection_exists(QDRANT_COLLECTION):
        print(f"Eski '{QDRANT_COLLECTION}' koleksiyonu siliniyor...")
        client.delete_collection(QDRANT_COLLECTION)
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    )

    qdrant = Qdrant(
        client=client,
        collection_name=QDRANT_COLLECTION,
        embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
    )
    qdrant.add_documents(parcalar)


def azure_searche_yukle(parcalar):
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    kimlik = AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"])
    ad = index_adi()

    # İndeks varsa silinir, şema değişikliği ve çift veri sorunu olmasın.
    index_client = SearchIndexClient(endpoint=endpoint, credential=kimlik)
    if ad in list(index_client.list_index_names()):
        print(f"Eski '{ad}' indeksi siliniyor...")
        index_client.delete_index(ad)
    index_client.create_index(index_semasi())

    print("Embedding'ler üretiliyor...")
    vektorler = azure_search_embeddings().embed_documents([p.page_content for p in parcalar])

    belgeler = [
        {
            "id": str(i),
            "content": parca.page_content,
            "source": Path(parca.metadata.get("source", "")).name,
            "page": parca.metadata.get("page"),
            "embedding": vektor,
        }
        for i, (parca, vektor) in enumerate(zip(parcalar, vektorler))
    ]

    search_client = SearchClient(endpoint=endpoint, index_name=ad, credential=kimlik)
    basarisiz = 0
    for i in range(0, len(belgeler), 500):
        sonuclar = search_client.upload_documents(belgeler[i : i + 500])
        basarisiz += sum(1 for s in sonuclar if not s.succeeded)
        print(f"     {min(i + 500, len(belgeler))}/{len(belgeler)} yüklendi")
    if basarisiz:
        raise SystemExit(f"Hata: {basarisiz} belge yüklenemedi.")


HEDEFLER = {
    "qdrant": qdranta_yukle,
    "azure_search": azure_searche_yukle,
}

if __name__ == "__main__":
    hedef = os.getenv("VECTOR_STORE", "qdrant").lower()
    if hedef not in HEDEFLER:
        raise SystemExit(f"Bilinmeyen VECTOR_STORE: '{hedef}'. Geçerli seçenekler: {list(HEDEFLER)}")

    parcalar = pdfleri_parcala(KAYNAK_KLASORU)
    print(f"\nToplam {len(parcalar)} parça. Hedef: {hedef}\n")
    HEDEFLER[hedef](parcalar)
    print("\nTamamlandı.")
