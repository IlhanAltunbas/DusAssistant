import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings

# Ücretsiz katmanın 50 MB sınırına sığmak için 1536 yerine 512 boyut.
# Yükleme ve sorgu aynı boyutu kullanmak zorunda, bu yüzden tek yerde tanımlı.
EMBEDDING_BOYUTU = 512


def index_adi():
    return os.getenv("AZURE_SEARCH_INDEX", "periodontoloji-notlari")


def azure_search_embeddings():
    return OpenAIEmbeddings(model="text-embedding-3-small", dimensions=EMBEDDING_BOYUTU)


def index_semasi() -> SearchIndex:
    return SearchIndex(
        name=index_adi(),
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String),
            SimpleField(name="page", type=SearchFieldDataType.Int32),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                hidden=True,
                # Vektörün ayrıca saklanan kopyası tutulmaz; sadece arama indeksinde yaşar.
                stored=False,
                vector_search_dimensions=EMBEDDING_BOYUTU,
                vector_search_profile_name="hnsw-profil",
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[VectorSearchProfile(name="hnsw-profil", algorithm_configuration_name="hnsw")],
        ),
    )


class AzureSearchRetriever(BaseRetriever):
    search_client: SearchClient
    embeddings: OpenAIEmbeddings
    k: int = 5

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query, *, run_manager):
        vektor = self.embeddings.embed_query(query)
        sonuclar = self.search_client.search(
            search_text=None,
            vector_queries=[VectorizedQuery(vector=vektor, k_nearest_neighbors=self.k, fields="embedding")],
            select=["content", "source", "page"],
            top=self.k,
        )
        return [
            Document(page_content=s["content"], metadata={"source": s["source"], "page": s["page"]})
            for s in sonuclar
        ]


def azure_search_retriever_olustur():
    # Uygulama sadece okuma yetkili query key kullanır; admin key yalnızca veri yükleme scriptinde.
    client = SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=index_adi(),
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_QUERY_KEY"]),
    )
    return AzureSearchRetriever(search_client=client, embeddings=azure_search_embeddings())
