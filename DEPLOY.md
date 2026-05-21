# EndoScan AI — Render.com'ga joylashtirish qo'llanmasi

Bu hujjat loyihani **Render.com** serveriga qadam-baqadam joylashtirishni
o'rgatadi. Avval xavfsizlik qismi tushuntiriladi, keyin deploy jarayoni.

---

## 1-QISM. Xavfsizlikda nima o'zgardi

Loyiha kodi ichida ochiq turgan maxfiy kalitlar topildi va ular `.env`
fayliga ko'chirildi. Asosiy struktura va mantiq O'ZGARMADI.

| Joy | Avval (xavfli) | Hozir (xavfsiz) |
|-----|----------------|------------------|
| `main.py` | Gemini API kaliti kod ichida | `os.getenv("GOOGLE_API_KEY")` |
| `api.py` | Gemini API kaliti kod ichida | `os.getenv("GOOGLE_API_KEY")` |
| `auth.py` | `SECRET_KEY = "your_secret_key"` | `os.getenv("JWT_SECRET_KEY")` |

Qo'shimcha yaratilgan fayllar:

- **`.env`** — haqiqiy maxfiy kalitlar (faqat sizning kompyuteringizda/serverda).
- **`.env.example`** — namuna shablon (boshqalar uchun, sirlar yo'q).
- **`.gitignore`** — `.env`, baza, rasmlar GitHub'ga ketmasligi uchun.
- **`Dockerfile`, `.dockerignore`, `start.sh`, `render.yaml`** — deploy fayllari.

### ⚠️ HOZIROQ BAJARING — eng muhim 3 ta ish

1. **Gemini API kalitini almashtiring.** Eski kalit
   (`AIzaSyBVA8r0B8D5AGqphr5qT_QGi0q-6goCJhc`) kod ichida ochiq turgan,
   ya'ni u **buzilgan** hisoblanadi. Uni darhol o'chiring:
   - https://aistudio.google.com/apikey ga kiring
   - Eski kalitni **o'chiring (Delete)**
   - **Yangi kalit** yarating va uni `.env` faylidagi `GOOGLE_API_KEY` ga qo'ying.

2. **`.env` faylini hech qachon GitHub'ga yuklamang.** `.gitignore` buni
   avtomatik to'sadi, lekin baribir tekshiring.

3. **Eski admin parolini almashtiring.** Eski `endoscan.db` ichida
   `admin / admin123` akkaunti bor. Yangi parol `.env` da yozilgan
   (`ENDOSCAN_ADMIN_PASSWORD`). Bu parol **faqat yangi baza yaratilganda**
   ishlaydi — pastdagi 6-bo'limga qarang.

---

## 2-QISM. Render haqida muhim ogohlantirish

Bu loyiha **og'ir** — ichida sun'iy intellekt kutubxonalari bor
(`torch`, `transformers`, CLIP model). Hozir `render.yaml` Render **Free**
demo varianti uchun sozlangan, lekin bepul servis resurslari cheklangan.

- ✅ **Render "Free"** demo/test uchun ishlatib ko'rish mumkin.
- ⚠️ Agar servis `Out of Memory` bilan o'chsa yoki juda sekin ochilsa,
  **Render "Standard"** yoki yengilroq model kerak bo'ladi.
- ⚠️ Free servis 15 daqiqa ishlatilmasa uxlaydi. Restart, redeploy yoki
  spin-down bo'lganda lokal SQLite baza va uploads o'chib ketadi.

Davom etamiz — quyida Render Free uchun yo'riqnoma.

---

## 3-QISM. Tayyorgarlik

Sizga kerak bo'ladi:

- **GitHub akkaunti** (https://github.com) — kod shu yerga yuklanadi.
- **Render akkaunti** (https://render.com) — GitHub orqali kirish mumkin.
- **Git** kompyuteringizda o'rnatilgan bo'lishi kerak
  (https://git-scm.com/download/win).

---

## 4-QISM. Loyihani GitHub'ga yuklash

Render kodni to'g'ridan-to'g'ri GitHub'dan oladi.

### 4.1. GitHub'da yangi repozitoriy yarating

1. https://github.com/new ga kiring.
2. Nom bering, masalan `endoscan-ai`.
3. **"Private"** (yopiq) tanlang — tibbiy loyiha, ochiq bo'lmasin.
4. Hech narsa qo'shmang (README, .gitignore — yo'q), **"Create"** bosing.

### 4.2. Kodni yuklang

PowerShell'ni oching va loyiha papkasiga kiring:

```powershell
cd W:\v3\v3

git init
git add .
git commit -m "EndoScan AI - xavfsizlik tuzatildi, deploy uchun tayyor"
git branch -M main
git remote add origin https://github.com/SIZNING_NOMINGIZ/endoscan-ai.git
git push -u origin main
```

> `SIZNING_NOMINGIZ` o'rniga o'z GitHub nomingizni yozing.

### 4.3. `.env` yuklanmaganini tekshiring

Bu juda muhim. Quyidagi buyruq **hech narsa chiqarmasligi** kerak:

```powershell
git ls-files | Select-String "^.env$"
```

Agar `.env` ro'yxatda chiqsa — `.gitignore` ishlamagan. To'xtang va menga ayting.

---

## 5-QISM. Render'da servis yaratish

### 5.1. Yangi Web Service

1. https://dashboard.render.com ga kiring.
2. **"New +"** → **"Web Service"** bosing.
3. GitHub akkauntingizni ulang va `endoscan-ai` repozitoriyini tanlang.

### 5.2. Sozlamalar

Render `render.yaml` faylini ko'rib, ko'p narsani avtomatik to'ldiradi.
Tekshiring va to'g'rilang:

| Maydon | Qiymat |
|--------|--------|
| **Name** | `endoscan-ai` |
| **Region** | `Frankfurt` (O'zbekistonga eng yaqini) |
| **Branch** | `main` |
| **Runtime / Language** | `Docker` |
| **Instance Type / Plan** | **`Free`** |

### 5.3. Maxfiy o'zgaruvchilarni (Environment Variables) kiritish

Bu eng muhim qadam. **"Environment"** bo'limida quyidagilarni qo'shing
(`.env` faylingizdagi qiymatlarni nusxalang):

| Key (nomi) | Value (qiymati) |
|------------|-----------------|
| `GOOGLE_API_KEY` | YANGI Gemini kalitingiz (1-qism, 1-ish) |
| `JWT_SECRET_KEY` | `.env` faylidagi uzun kalit |
| `ENDOSCAN_ADMIN_USERNAME` | `admin` |
| `ENDOSCAN_ADMIN_PASSWORD` | `.env` faylidagi admin parol |

> ⚠️ Bu qiymatlar Render dashboard'ida saqlanadi, GitHub'ga ketmaydi.
> `.env` faylining o'zi serverga yuklanmaydi — Render kalitlarni shu
> yerdan oladi.

### 5.4. Deploy

**"Create Web Service"** (yoki "Deploy") bosing. Render:

1. Docker image'ni quradi (torch va AI modeli yuklanadi — **10–15 daqiqa**
   ketadi, sabr qiling).
2. Konteynerni ishga tushiradi.
3. Sizga manzil beradi: `https://endoscan-ai.onrender.com` kabi.

Loglarni real vaqtda **"Logs"** bo'limida kuzatishingiz mumkin.
`FastAPI ishga tushmoqda` degan satr chiqsa — server tayyor.

---

## 6-QISM. Baza va admin akkaunti

Render konteyneri **vaqtinchalik** — har deploy'da fayl tizimi tozalanadi.

- **Doimiy disksiz:** har yangi deploy'da `endoscan.db` qaytadan yaratiladi.
  Admin akkaunti har safar `.env`/Environment dagi paroldan tiklanadi.
  Ro'yxatdan o'tgan foydalanuvchilar va tarix o'chib ketadi
  (demo/test uchun bu yetarli).

- **Doimiy disk bilan:** bu faqat pullik planda ishlaydi. Free deploy uchun
  `render.yaml` ichidan disk olib tashlangan.

**Birinchi kirish:** server ishga tushgach, `https://...onrender.com/admin-login`
ga kiring va `.env` dagi `admin` / parol bilan kiring. Kirgandan keyin
parolni almashtirishni unutmang.

> Eski `endoscan.db` (admin123 bilan) `.dockerignore` orqali konteynerga
> umuman tushmaydi — server har doim toza baza bilan boshlanadi.

---

## 7-QISM. Tekshirish

Server manzili (`https://endoscan-ai.onrender.com`) ni brauzerda oching:

- `/` — bosh sahifa
- `/register` — ro'yxatdan o'tish
- `/login` — foydalanuvchi kirishi
- `/admin-login` — admin kirishi
- `/analyze` — rasm tahlili (kirgandan keyin)

Agar tahlil sahifasida xato chiqsa — `GOOGLE_API_KEY` to'g'ri kiritilganini
tekshiring (Render → Environment).

---

## 8-QISM. Keyingi deploy (kodni yangilash)

Kodga o'zgartirish kiritsangiz:

```powershell
cd W:\v3\v3
git add .
git commit -m "o'zgarish haqida izoh"
git push
```

Render `push` ni sezadi va avtomatik qayta deploy qiladi.

---

## Qo'shimcha xavfsizlik tavsiyalari (ixtiyoriy)

Bular keyinroq, vaqt bo'lganda:

1. **CORS:** `main.py` da `origins = ['*']` — hamma saytga ruxsat berilgan.
   Faqat o'z domeningizni qoldirsangiz xavfsizroq.
2. **Parol himoyasi:** parollar `SHA-256` bilan saqlanyapti. `bcrypt` yoki
   `argon2` ishlatish ancha xavfsizroq (parol "tuz"i bilan).
3. **`frontend/.git`:** loyiha ichida keraksiz `.git` papkasi bor —
   `frontend/.git` ni o'chirib tashlang.
4. **Ikki frontend:** `frontend/` papkasi eski va ishlatilmaydi
   (dastur `frontendnew/` ni ishlatadi) — uni o'chirsa bo'ladi.
5. **HTTPS:** Render `onrender.com` manziliga HTTPS'ni avtomatik beradi —
   bu yaxshi, qo'shimcha sozlash shart emas.

---

## Tez yordam (muammolar)

| Muammo | Yechim |
|--------|--------|
| Server `Out of Memory` bilan o'chyapti | Free resurs yetmayapti; `Standard` plan yoki yengilroq model kerak |
| `JWT_SECRET_KEY ... sozlanmagan` xatosi | Render Environment'ga `JWT_SECRET_KEY` qo'shing |
| Tahlil ishlamayapti | `GOOGLE_API_KEY` yangi va to'g'ri ekanini tekshiring |
| Build juda uzoq | Bu normal — torch+AI modeli ~10-15 daqiqa |
| Statistika "namuna" raqamlarni ko'rsatyapti | Java servisi ishlamayapti — Logs'ni tekshiring |
