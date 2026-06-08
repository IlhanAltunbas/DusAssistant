import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def retriever_olustur(collection_name="periodontoloji_notlari"):
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    qdrant = Qdrant(
        client=client, 
        collection_name=collection_name, 
        embeddings=embeddings
    )
    return qdrant.as_retriever(search_kwargs={"k": 5})

llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001", 
    temperature=0
)

#Promptu sadece System (Kurallar) seviyesine taşıdık.
system_template = """Sen uzman bir DUS (Diş Hekimliğinde Uzmanlık Sınavı) Periodontoloji asistanısın.
SADECE aşağıdaki kaynak metinleri (Context) kullanarak sorulara cevap ver.
Eğer cevap kaynaklar arasında değilse KESİNLİKLE uydurma ve şunu söyle: "Bu kaynakların içinde bu soruya dair bir bilgi yok."
Eğer cevap kısmi olarak içeriliyorsa, kaynağa dayalı olan en iyi cevabı sağla.

Kaynak Metinler (Context):
{context}"""

# ChatPromptTemplate'i mesaj tiplerine göre ayırdık
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_template),
    # Langchain'e sohbet geçmişini (chat_history) buraya koymasını söylüyoruz
    ("placeholder", "{chat_history}"),
    HumanMessagePromptTemplate.from_template("{question}")
])

def dokumanlari_birlestir(docs):
    return "\n\n".join(doc.page_content for doc in docs)

retriever = retriever_olustur()

# Zinciri oluşturuyoruz
rag_zinciri = (
    RunnablePassthrough.assign(
        context=lambda x: dokumanlari_birlestir(retriever.invoke(x["question"]))
    )
    | prompt
    | llm
    | StrOutputParser()
)

#Fonksiyon artık gecmis (history) listesini de alıyor.
def asistana_sor(soru: str, gecmis: list = None):
    print("Kaynaklar taranıyor ve cevap üretiliyor...\n")
    
    # Mobil taraftan gelen string geçmiş listesini LangChain mesaj objelerine çeviriyoruz
    chat_history_messages = []
    if gecmis:
        for msg in gecmis:
            if msg.startswith("User:"):
                chat_history_messages.append(HumanMessage(content=msg.replace("User: ", "", 1)))
            elif msg.startswith("Assistant:"):
                chat_history_messages.append(AIMessage(content=msg.replace("Assistant: ", "", 1)))

    # Zinciri çağırırken soruyu ve çevrilmiş mesaj geçmişini veriyoruz
    cevap = rag_zinciri.invoke({
        "question": soru,
        "chat_history": chat_history_messages
    })
    return cevap

if __name__ == "__main__":
    # Test Senaryosu
    test_gecmis = ["User: Merhaba!", "Assistant: Merhaba, ben bir Periodontoloji uzmanıyım."]
    test_sorusu = "Ben sana az önce ne dedim?" 
    
    print(f"Soru: {test_sorusu}")
    yanit = asistana_sor(test_sorusu, test_gecmis)
    print("Asistanın Cevabı:", yanit)