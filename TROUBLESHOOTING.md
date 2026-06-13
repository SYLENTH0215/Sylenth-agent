# 🔧 SYLENTH Agent - Muammolarni Hal Qilish

## Tez-tez Uchraydigan Xatolar

### 1. Bot ishga tushmayapti

#### Xato: `ValueError: ❌ BOT_TOKEN muhim!`
**Sabab:** `.env` faylida `BOT_TOKEN` yo'q

**Yechim:**
```bash
cp .env.example .env
nano .env  # BOT_TOKEN kiriting
```

#### Xato: `ValueError: ❌ ADMIN_ID noto'g'ri formatda!`
**Sabab:** ADMIN_ID raqam emas

**Yechim:**
```bash
# .env faylda qo'shtirnoqsiz raqam
ADMIN_ID=123456789  # ✅ To'g'ri
```

### 2. OpenAI API Xatolari

#### Xato: `Invalid API key`
**Yechim:** [OpenAI Platform](https://platform.openai.com/api-keys) da yangi key yarating

#### Xato: `Rate limit exceeded`
**Yechim:** 1-2 daqiqa kuting

#### Xato: `Insufficient credits`
**Yechim:** [Billing](https://platform.openai.com/account/billing) da kredit qo'shing

### 3. FFmpeg Xatolari

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**MacOS:**
```bash
brew install ffmpeg
```

**Windows:** [FFmpeg yuklab](https://ffmpeg.org/download.html) oling

### 4. Import Xatolari

```bash
# Virtual environment aktivlash
source venv/bin/activate

# Dependencies qayta o'rnatish
pip install -r requirements.txt
```

### 5. Database Xatolari

```bash
# Database qayta yaratish
rm sylenth.db
python -c "from database import init_db; init_db()"
```

### 6. GitHub Actions

**Secrets qo'shish:**
1. Settings → Secrets and variables → Actions
2. `BOT_TOKEN`, `OPENAI_API_KEY`, `ADMIN_ID` qo'shing

### 7. Docker Xatolari

```bash
# Docker build (clean)
docker-compose build --no-cache
docker-compose up -d

# Logs
docker logs -f sylenth-bot
```

## Yordam

- **Issues:** [GitHub](https://github.com/SYLENTH0215/Sylenth-agent/issues)
- **Telegram:** [@sylenth_uz](https://t.me/sylenth_uz)
- **Docs:** [README](README.md) | [SETUP](SETUP.md) | [API](API.md)
