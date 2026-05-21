# ============================================================
#  EndoScan AI — Render.com uchun Docker image
#  Bitta konteyner ichida: Python (FastAPI) + Java (statistika)
# ============================================================
FROM python:3.12-slim

# Java (statistika servisi uchun) va C/C++ kompilyator (chromadb uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-jdk \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch'ning faqat CPU versiyasini o'rnatamiz (kichikroq, serverda GPU yo'q)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Qolgan Python kutubxonalari (kesh uchun avval faqat requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CLIP modelini oldindan yuklab image ichiga joylaymiz
# (shunda birinchi tahlil so'rovi sekin bo'lib qolmaydi)
RUN python -c "from transformers import CLIPModel, CLIPProcessor; \
    CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); \
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"

# Loyiha fayllarini nusxalash
COPY . .

# Java statistika servisini kompilyatsiya qilish
RUN mkdir -p java_stats_service/out \
    && javac -encoding UTF-8 -d java_stats_service/out java_stats_service/src/StatsServer.java

# Ishga tushirish skripti (Windows CRLF'ni tozalaymiz)
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000
CMD ["bash", "start.sh"]
