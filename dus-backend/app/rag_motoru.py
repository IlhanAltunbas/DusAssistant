from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
import anthropic
import openai

from .providers.factory import get_llm
from .retrievers.factory import get_retriever

# Tekrar deneme tek katmanda, SDK'ların içinde yapılır: openai, anthropic ve Azure AI Search istemcileri
# geçici hatalarda (429, 408, 5xx, bağlantı) sadece başarısız çağrıyı tekrar dener ve Retry-After'a uyar.
# Üstüne ikinci bir retry katmanı eklemek denemeleri katlıyordu (1 soru -> 12 LLM isteği).
# Bu liste SDK denemeleri tükendikten sonra kullanıcıya hangi mesajın gösterileceğine karar verir.
GECICI_HATALAR = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


load_dotenv()

llm = get_llm()

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

retriever = get_retriever()

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

    chat_history_messages = []
    if gecmis:
        for msg in gecmis:
            if msg.startswith("User:"):
                chat_history_messages.append(HumanMessage(content=msg.replace("User: ", "", 1)))
            elif msg.startswith("Assistant:"):
                chat_history_messages.append(AIMessage(content=msg.replace("Assistant: ", "", 1)))

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

    