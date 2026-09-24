from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import anthropic
import openai

from .providers.factory import get_llm
from .retrievers.factory import get_retriever

# Rate limit, timeout ve bağlantı kopması gibi geçici hatalar - bunlarda tekrar denemek mantıklı.
# Auth/quota/geçersiz istek gibi kalıcı hatalarda tekrar denemek sadece kullanıcıyı bekletir.
GECICI_HATALAR = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
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
@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type(GECICI_HATALAR),
    reraise=True,
)
def _zinciri_calistir(girdi: dict):
    return rag_zinciri.invoke(girdi)

def asistana_sor(soru: str, gecmis: list = None):
    print("Kaynaklar taranıyor ve cevap üretiliyor...\n")

    chat_history_messages = []
    if gecmis:
        for msg in gecmis:
            if msg.startswith("User:"):
                chat_history_messages.append(HumanMessage(content=msg.replace("User: ", "", 1)))
            elif msg.startswith("Assistant:"):
                chat_history_messages.append(AIMessage(content=msg.replace("Assistant: ", "", 1)))

    cevap = _zinciri_calistir({
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

    