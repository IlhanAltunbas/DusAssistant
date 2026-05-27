import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http import models

# 1. .env dosyasındaki gizli anahtarları sisteme yükle
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def verileri_hazirla_ve_yukle(pdf_yolu, collection_name="periodontoloji_notlari"):
    print(f"[{pdf_yolu}] okunuyor...")
    
    # 2. PDF Yükleme ve Senin Chunk Stratejin
    loader = PyPDFLoader(pdf_yolu)
    sayfalar = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True
    )
    
    parcalar = text_splitter.split_documents(sayfalar)
    print(f"Toplam {len(parcalar)} adet parça oluşturuldu. Qdrant'a gönderiliyor...")

    # 3. Embedding Modeli (En maliyet-etkin ve başarılı model)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # 4. Qdrant İstemcisine Bağlantı
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 5. Koleksiyon (Index) Kontrolü
    try:
        # Koleksiyon zaten varsa hata vermez, verileri üstüne ekler
        client.get_collection(collection_name=collection_name)
        print(f"'{collection_name}' koleksiyonu bulundu, veriler üzerine ekleniyor.")
    except:
        # Koleksiyon yoksa, OpenAI embedding boyutuna (1536) uygun yeni koleksiyon açar
        print(f"'{collection_name}' koleksiyonu bulunamadı, yeni oluşturuluyor.")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

    # 6. Verileri Vektör Veritabanına Yükleme
    qdrant = Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)
    qdrant.add_documents(parcalar)
    
    print("Başarılı! Tüm veriler vektöre çevrilip veritabanına kaydedildi.")

# Script doğrudan çalıştırıldığında burası tetiklenir
if __name__ == "__main__":
    # TODO: Burayı kendi PDF dosyanın adıyla değiştireceksin
    dosya_yolu = "kaynaklar/Clinical_Periodontology.pdf"
    
    if os.path.exists(dosya_yolu):
        verileri_hazirla_ve_yukle(dosya_yolu)
    else:
        print(f"Hata: '{dosya_yolu}' bulunamadı. Lütfen klasörü ve PDF adını kontrol et.")