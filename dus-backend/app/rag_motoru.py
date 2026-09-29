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

# Talimatlar İngilizce: Türkçe prompt, İngilizce sorulara da Türkçe cevap verdiriyordu.
# Dil kuralı kaynak metinlerin sonunda, yani soruya en yakın yerde; uzun context araya girince
# baştaki kurala uyulmuyordu.
system_template = """You are an expert periodontology assistant for DUS, the Turkish dental specialty exam.
Answer ONLY from the source texts (Context) below.
If the answer is not in the sources, do NOT make anything up. Reply with exactly this sentence, in the user's language:
- Turkish: "Bu kaynakların içinde bu soruya dair bir bilgi yok."
- English: "There is no information about this question in these sources."
If the sources only partially answer the question, give the best answer the sources support.

Source texts (Context):
{context}

LANGUAGE RULE: Always write your answer in the language of the user's latest question (Turkish question -> Turkish answer, English question -> English answer). The source texts may be in a different language; translate as needed."""

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

# Arama sadece son soruyu görür. "Bunlardan hangisi en güçlüsü?" gibi bir takip sorusunda konu
# (periodontitis) sorguda geçmediği için doğru parça geriye düşüyordu. Geçmiş varsa soru önce
# geçmişe bakmadan anlaşılır hale getirilir; cevabı üreten LLM ise orijinal soruyu ve geçmişi görür.
yeniden_yazma_promptu = ChatPromptTemplate.from_messages([
    ("system", "Rewrite the user's latest question as a standalone question that can be understood "
               "without the chat history, replacing words like 'these' or 'it' with what they refer to. "
               "Keep the language of the question. Do NOT answer it. If it is already standalone, "
               "return it unchanged. Return only the question."),
    ("placeholder", "{chat_history}"),
    ("human", "{question}"),
])
sorgu_yeniden_yazici = yeniden_yazma_promptu | llm | StrOutputParser()


def arama_sorgusu(girdi: dict) -> str:
    # İlk soruda geçmiş yok; ek LLM çağrısına gerek yok.
    if not girdi.get("chat_history"):
        return girdi["question"]
    return sorgu_yeniden_yazici.invoke(girdi)


# Zinciri oluşturuyoruz
rag_zinciri = (
    RunnablePassthrough.assign(arama_sorgusu=arama_sorgusu)
    | RunnablePassthrough.assign(
        context=lambda x: dokumanlari_birlestir(retriever.invoke(x["arama_sorgusu"]))
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

    