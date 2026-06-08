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

def veritabanini_sifirla(client, collection_name):
    # Eğer koleksiyon varsa sil (Duplicate/Çift veri oluşumunu engellemek için)
    try:
        client.get_collection(collection_name)
        print(f"Eski '{collection_name}' koleksiyonu bulundu. Temizleniyor...")
        client.delete_collection(collection_name)
    except:
        pass # Koleksiyon yoksa yola devam et

    # Yepyeni, tertemiz bir koleksiyon oluştur
    print(f"Yeni '{collection_name}' koleksiyonu oluşturuluyor...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    )

def pdf_isle_ve_qdranta_gonder(pdf_yolu, qdrant):
    print(f"\n---> İşleniyor: {pdf_yolu} ")
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
    print(f"Toplam {len(parcalar)} adet parça oluşturuldu. Veritabanına gönderiliyor...")
    
    # Parçaları vektöre çevirip Qdrant'a ekle
    qdrant.add_documents(parcalar)
    print(f"'{pdf_yolu}' başarıyla eklendi!")

if __name__ == "__main__":
    klasor_yolu = "kaynaklar"
    collection_name = "periodontoloji_notlari"

    print("İşlem başlıyor. Qdrant'a bağlanılıyor...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # 1. Eski veritabanını temizle
    veritabanini_sifirla(client, collection_name)

    # 2. Qdrant nesnemizi oluştur
    qdrant = Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)

    # 3. 'kaynaklar' klasöründeki tüm PDF'leri bul ve döngüye sok
    if os.path.exists(klasor_yolu):
        pdf_dosyalari = [f for f in os.listdir(klasor_yolu) if f.endswith('.pdf')]
        
        if not pdf_dosyalari:
            print(f"Hata: '{klasor_yolu}' klasöründe hiç PDF dosyası bulunamadı!")
        else:
            print(f"Toplam {len(pdf_dosyalari)} adet PDF bulundu. Yükleme başlıyor...\n")
            for dosya_adi in pdf_dosyalari:
                tam_yol = os.path.join(klasor_yolu, dosya_adi)
                pdf_isle_ve_qdranta_gonder(tam_yol, qdrant)
                
            print("\nTEBRİKLER! Tüm PDF'ler başarıyla parçalandı ve vektör veritabanına kaydedildi.")
    else:
        print(f"Hata: '{klasor_yolu}' klasörü bulunamadı. Lütfen klasörün var olduğundan emin ol.")