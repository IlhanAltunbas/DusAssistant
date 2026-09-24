# 3.12: langchain 0.1.x'in istediği numpy 1.26 için 3.13'te hazır wheel yok, slim image'da derlenemiyor.
FROM python:3.12-slim

WORKDIR /app

# Kütüphaneler koddan önce kurulur: kod değişince bu katman önbellekten gelir.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

# Container içinde 127.0.0.1 dışarıdan erişilemez, 0.0.0.0 tüm arayüzleri dinler.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
