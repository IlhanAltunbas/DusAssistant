import os

# Test ayarları uygulama modülleri import edilmeden önce yazılmalı: guvenlik.py anahtarı ve sınırları
# import anında okur. load_dotenv mevcut değişkenlerin üzerine yazmadığı için .env'deki değerler
# testleri etkilemez; testler her makinede ve CI'da aynı sınırlarla çalışır.
os.environ["APP_API_KEY"] = "test-anahtari"
os.environ["RATE_LIMIT_PER_IP_MINUTE"] = "5"
os.environ["RATE_LIMIT_PER_IP_DAY"] = "20"
os.environ["RATE_LIMIT_GLOBAL_DAY"] = "30"
