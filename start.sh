#!/usr/bin/env bash
# EndoScan AI ishga tushirish skripti (bitta konteyner ichida 2 ta servis)
set -e

# Render bergan port (mahalliy test uchun 8000)
APP_PORT="${PORT:-8000}"

# Agar doimiy disk ulangan bo'lsa — baza va rasmlarni o'sha yerda saqlaymiz,
# shunda har deploy'da ma'lumotlar o'chib ketmaydi.
if [ -d /var/data ]; then
  echo "[start] Doimiy disk topildi: /var/data"
  mkdir -p /var/data/uploads
  if [ -d /app/uploads ] && [ ! -L /app/uploads ]; then
    rm -rf /app/uploads
  fi
  ln -sfn /var/data/uploads /app/uploads
  ln -sfn /var/data/endoscan.db /app/endoscan.db
fi

# Java statistika servisi — ichki 8081-portda, fon rejimida
echo "[start] Java statistika servisi ishga tushmoqda (port 8081)..."
PORT=8081 PYTHON_STATS_BASE_URL="http://127.0.0.1:${APP_PORT}" \
  java -cp /app/java_stats_service/out StatsServer &

# Python FastAPI — Render bergan portda (asosiy servis)
echo "[start] FastAPI ishga tushmoqda (port ${APP_PORT})..."
exec uvicorn main:app --host 0.0.0.0 --port "${APP_PORT}"
