import os

# Test ayarları uygulama modülleri import edilmeden önce yazılmalı: guvenlik.py anahtarı ve sınırları,
# rag_motoru.py LLM ve arama istemcilerini import anında kurar. load_dotenv mevcut değişkenlerin
# üzerine yazmadığı için .env'deki değerler testleri etkilemez; testler her makinede ve CI'da aynı
# ayarlarla çalışır.
os.environ["APP_API_KEY"] = "test-anahtari"
os.environ["RATE_LIMIT_PER_IP_MINUTE"] = "5"
os.environ["RATE_LIMIT_PER_IP_DAY"] = "20"
os.environ["RATE_LIMIT_GLOBAL_DAY"] = "30"

# İstemciler kurulurken ağa çıkmaz, sadece bu ayarları okur. Adresler .invalid: hiçbir zaman
# çözülmeyen bir alan adı, yani bir test yanlışlıkla gerçek çağrı yaparsa Azure'a ulaşamaz, hemen hata verir.
os.environ["LLM_PROVIDER"] = "azure"
os.environ["VECTOR_STORE"] = "azure_search"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.invalid"
os.environ["AZURE_OPENAI_API_KEY"] = "test"
os.environ["AZURE_OPENAI_DEPLOYMENT"] = "test"
os.environ["AZURE_SEARCH_ENDPOINT"] = "https://test.invalid"
os.environ["AZURE_SEARCH_QUERY_KEY"] = "test"
os.environ["OPENAI_API_KEY"] = "test"

import pytest  # noqa: E402

from app import guvenlik  # noqa: E402


@pytest.fixture(autouse=True)
def sayaclari_sifirla():
    # Rate limit sayaçları modül düzeyinde tutuluyor; bir testin istekleri diğerine taşınmasın.
    guvenlik._ip_istekleri.clear()
    guvenlik._genel_istekler.clear()
    yield
    guvenlik._ip_istekleri.clear()
    guvenlik._genel_istekler.clear()
