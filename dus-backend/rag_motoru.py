import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from qdrant_client import QdrantClient

# 1. Ortam Değişkenlerini Yükle
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# 2. Retriever (Geri Getirici) Kurulumu
# Qdrant'a bağlanıp, sorulan soruya en yakın 5 (k=5) metin parçasını getirmesini istiyoruz.
def retriever_olustur(collection_name="periodontoloji_notlari"):
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    qdrant = Qdrant(
        client=client, 
        collection_name=collection_name, 
        embeddings=embeddings
    )
    return qdrant.as_retriever(search_kwargs={"k": 5})

# 3. LLM (Claude) Kurulumu
llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001", 
    temperature=0
)

# Prompt Şablonu
prompt_template = """Sen bir Periodontoloji uzmanısın. SADECE aşağıdaki kaynak metinleri kullanarak sorulara cevap ver. 
Eğer cevap kaynaklar arasında değilse şunu söyle: "Bu kaynakların içinde bu soruya dair bir bilgi yok."
Eğer cevap kısmi olarak içeriliyorsa, kaynağa dayalı olan en iyi cevabı sağla.

Kaynak Metinler:
{context}

Soru: {question}
Cevap:"""

prompt = ChatPromptTemplate.from_template(prompt_template)

# 5. Dokümanları (Chunk'ları) Metne Çeviren Yardımcı Fonksiyon
def dokumanlari_birlestir(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 6. RAG Zincirinin (Chain) Kurulması
retriever = retriever_olustur()

rag_zinciri = (
    {"context": retriever | dokumanlari_birlestir, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 7. Dışarıdan Çağırılacak Ana Fonksiyon
def asistana_sor(soru: str):
    print("Kaynaklar taranıyor ve cevap üretiliyor...\n")
    cevap = rag_zinciri.invoke(soru)
    return cevap

# Sadece bu dosyayı test etmek için
if __name__ == "__main__":
    test_sorusu = "Gingivitis nedir ve temel belirtileri nelerdir?" 
    print(f"Soru: {test_sorusu}")
    
    yanit = asistana_sor(test_sorusu)
    print("Asistanın Cevabı:")
    print("-" * 50)
    print(yanit)
    print("-" * 50)
