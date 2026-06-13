# SYLENTH Agent - To'liq O'rnatish Qo'llanmasi

## Tezkor Boshlash (5 daqiqa)

### 1. Telegram Bot yaratish

1. Telegram'da [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `SYLENTH Assistant`)
4. Bot username kiriting (masalan: `sylenth_assistant_bot`)
5. BotFather sizga TOKEN beradi: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
6. Tokenni saqlang - bu sizning `BOT_TOKEN`

### 2. OpenAI API Key olish

1. [OpenAI Platform](https://platform.openai.com/api-keys) ga o'ting
2. Ro'yxatdan o'ting yoki kiring
3. "Create new secret key" tugmasini bosing
4. Key nomi kiriting (masalan: `SYLENTH Bot`)
5. API key ko'rsatiladi - **faqat bir marta ko'rinadi!**
6. Key'ni xavfsiz joyga saqlang - bu sizning `OPENAI_API_KEY`

**Muhim:** OpenAI API pullik xizmat. $5-10 kredit yetarli bo'ladi.

### 3. Telegram ID ni aniqlash

1. Telegram'da [@userinfobot](https://t.me/userinfobot) ga o'ting
2. Botga `/start` yuboring
3. Bot sizning ID raqamingizni ko'rsatadi
4. Bu raqam - sizning `ADMIN_ID`

## Mahalliy O'rnatish (Local Development)

### Windows

```bash
# 1. Repository'ni klonlash
git clone https://github.com/SYLENTH0215/Sylenth-agent.git
cd Sylenth-agent

# 2. Virtual environment yaratish
python -m venv venv
venv\Scripts\activate

# 3. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 4. .env faylni yaratish
copy .env.example .env
# .env faylni notepad bilan ochib to'ldiring

# 5. Botni ishga tushirish
python main.py
```

### Linux / Mac

```bash
# 1. Repository'ni klonlash
git clone https://github.com/SYLENTH0215/Sylenth-agent.git
cd Sylenth-agent

# 2. Virtual environment yaratish
python3 -m venv venv
source venv/bin/activate

# 3. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 4. .env faylni yaratish
cp .env.example .env
nano .env  # yoki vim, code, etc.

# 5. FFmpeg o'rnatish (video yuklash uchun)
# Ubuntu/Debian:
sudo apt update && sudo apt install -y ffmpeg

# MacOS:
brew install ffmpeg

# 6. Botni ishga tushirish
python3 main.py
```

## .env Fayl To'ldirish

`.env` faylni oching va quyidagi ma'lumotlarni kiriting:

```env
# MAJBURIY
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
ADMIN_ID=123456789

# OPSIONAL
REQUIRED_CHANNEL=@your_channel_username
GROQ_KEY=gsk_xxxxxxxxxxxx
FLOOD_RATE=1.5
BAN_THRESHOLD=5
MAX_FILE_MB=45
```

### Majburiy parametrlar:
- `BOT_TOKEN` - BotFather'dan olgan token
- `OPENAI_API_KEY` - OpenAI API kaliti
- `ADMIN_ID` - Sizning Telegram ID

### Opsional parametrlar:
- `REQUIRED_CHANNEL` - Obuna majburlash uchun kanal
- `GROQ_KEY` - Groq API (hozircha ishlatilmaydi)
- `FLOOD_RATE` - Spam himoyasi (soniyada)
- `BAN_THRESHOLD` - Avtomatik ban uchun ogohlantirish limiti
- `MAX_FILE_MB` - Maksimal fayl hajmi (MB)

## Server O'rnatish (Ubuntu/Debian)

### VPS/Dedicated Server

```bash
# 1. Serverni yangilash
sudo apt update && sudo apt upgrade -y

# 2. Python va kerakli paketlar
sudo apt install -y python3 python3-pip python3-venv git ffmpeg

# 3. Repository klonlash
cd /opt
sudo git clone https://github.com/SYLENTH0215/Sylenth-agent.git
cd Sylenth-agent

# 4. Virtual environment
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# 5. .env faylni sozlash
sudo nano .env
# Yuqoridagi ma'lumotlarni kiriting

# 6. Systemd service yaratish
sudo nano /etc/systemd/system/sylenth-bot.service
```

### Systemd Service fayli:

```ini
[Unit]
Description=SYLENTH AI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Sylenth-agent
Environment="PATH=/opt/Sylenth-agent/venv/bin"
ExecStart=/opt/Sylenth-agent/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Service'ni ishga tushirish:

```bash
# Service'ni yoqish
sudo systemctl daemon-reload
sudo systemctl enable sylenth-bot
sudo systemctl start sylenth-bot

# Status tekshirish
sudo systemctl status sylenth-bot

# Loglarni ko'rish
sudo journalctl -u sylenth-bot -f
```

## GitHub Actions (Bepul 24/7)

### 1. Repository'ni fork qiling

GitHub'da "Fork" tugmasini bosing.

### 2. Secrets qo'shish

1. Fork qilgan repository → Settings → Secrets and variables → Actions
2. "New repository secret" tugmasini bosing
3. Quyidagi secretlarni qo'shing:

| Name | Value | Misol |
|------|-------|-------|
| `BOT_TOKEN` | Telegram bot token | `1234567890:ABC...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-xxx...` |
| `ADMIN_ID` | Sizning Telegram ID | `123456789` |
| `REQUIRED_CHANNEL` | Kanal username (opsional) | `@mychannel` |

### 3. Workflow yoqish

1. Repository → Actions
2. "I understand my workflows, go ahead and enable them" tugmasini bosing
3. Workflow avtomatik ishga tushadi

### 4. Tekshirish

- Actions → Latest workflow run → Loglarni ko'ring
- Bot Telegram'da ishlayotganini tekshiring

## Docker (Advanced)

### Dockerfile yaratish:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Docker bilan ishga tushirish:

```bash
# Image yaratish
docker build -t sylenth-agent .

# Container ishga tushirish
docker run -d \
  --name sylenth-bot \
  --env-file .env \
  --restart unless-stopped \
  sylenth-agent

# Loglarni ko'rish
docker logs -f sylenth-bot

# To'xtatish
docker stop sylenth-bot
docker rm sylenth-bot
```

### Docker Compose:

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  bot:
    build: .
    container_name: sylenth-bot
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./downloads:/app/downloads
      - ./sylenth.db:/app/sylenth.db
```

```bash
# Ishga tushirish
docker-compose up -d

# Loglar
docker-compose logs -f

# To'xtatish
docker-compose down
```

## Xatoliklarni Bartaraf Qilish

### Bot ishga tushmayapti

**Xato:** `ValueError: ❌ BOT_TOKEN muhim!`
**Yechim:** `.env` faylda `BOT_TOKEN` to'g'ri kiritilganligini tekshiring

**Xato:** `ValueError: ❌ ADMIN_ID noto'g'ri formatda!`
**Yechim:** `ADMIN_ID` faqat raqam bo'lishi kerak (qo'shtirnoqsiz)

### OpenAI xatolari

**Xato:** `Invalid API key`
**Yechim:** OpenAI API kalitingiz to'g'riligini tekshiring

**Xato:** `Insufficient credits`
**Yechim:** OpenAI hisobingizga kredit qo'shing

**Xato:** `Rate limit exceeded`
**Yechim:** Biroz kuting yoki tarif rejangizni oshiring

### Video yuklab olish ishlamayapti

**Xato:** `FFmpeg not found`
**Yechim:** 
```bash
# Linux
sudo apt install ffmpeg

# Mac
brew install ffmpeg

# Windows - https://ffmpeg.org/download.html
```

### GitHub Actions ishlamayapti

1. Actions → Failed workflow → Xatoni o'qing
2. Secrets to'g'ri kiritilganligini tekshiring
3. Workflow fayli syntax to'g'ri ekanligini tasdiqlang

## Qo'shimcha Konfiguratsiya

### Kanal obunasini majburiy qilish

```env
REQUIRED_CHANNEL=@your_channel_username
```

Bot foydalanuvchilarni avval kanalga obuna bo'lishga majbur qiladi.

### Spam himoyasini sozlash

```env
FLOOD_RATE=1.5      # Xabarlar orasidagi minimal vaqt (soniya)
BAN_THRESHOLD=5      # Necha marta spam qilsa ban
```

### Fayl hajmi limitini o'zgartirish

```env
MAX_FILE_MB=45  # Maksimal 50MB (Telegram limit)
```

## Texnik Yordam

Muammolarga duch kelsangiz:

1. [Issues](https://github.com/SYLENTH0215/Sylenth-agent/issues) ni tekshiring
2. Yangi issue oching (xato tavsifi, loglar bilan)
3. Telegram: [@sylenth_uz](https://t.me/sylenth_uz)

---

**Muvaffaqiyat tilaymiz! 🚀**
