# Sylenth Agent Bot

Aqlli, xavfsiz va ko'p funksiyali Telegram bot - OpenAI GPT bilan ishlaydi.

## Xususiyatlar

- **AI Suhbat** - Sun'iy intellekt bilan o'zbekcha suhbatlashing
- **Xotira** - Bot foydalanuvchini eslab qoladi va moslashadi
- **Guruh qo'llab-quvvatlash** - Guruhlarda @mention yoki reply orqali murojaat
- **Musiqa yuklab olish** - Qo'shiq nomini yozing, bot topib beradi
- **Video yuklab olish** - YouTube, Instagram, TikTok, Facebook havolalarini yuboring
- **Internet qidiruv** - DuckDuckGo orqali ishonchli ma'lumot
- **Xavfsizlik filtri** - Nojoʻya kontentdan himoya

## O'rnatish

### 1. Repozitoriyani klonlash

```bash
git clone https://github.com/username/Sylenth-agent.git
cd Sylenth-agent
```

### 2. .env faylini sozlash

`.env.example` faylini `.env` ga nusxalang va to'ldiring:

```bash
cp .env.example .env
```

Kerakli o'zgaruvchilar:
- `BOT_TOKEN` - Telegram BotFather dan olingan token
- `OPENAI_API_KEY` - OpenAI API kaliti
- `ADMIN_ID` - Admin Telegram ID raqami

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Botni ishga tushirish

```bash
python main.py
```

## Buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni ishga tushirish |
| `/help` | Yordam sahifasi |
| `/clear` | Suhbat tarixini tozalash |
| `/search <so'rov>` | Internetdan qidirish |
| `/music <nomi>` | Musiqa yuklab olish |

## Foydalanish

### AI Suhbat
Botga istalgan savolingizni yozing - u javob beradi.

### Video yuklash
YouTube, Instagram, TikTok yoki Facebook video havolasini yuboring - bot yuklab beradi.

### Musiqa qidirish
Qo'shiq nomini yozing yoki `/music` buyrug'idan foydalaning.

### Guruhda foydalanish
Botni guruhga qo'shing va `@bot_username savol` yoki botning xabariga reply qiling.

## Texnologiyalar

- **Python 3.11+**
- **aiogram 3.x** - Telegram Bot API framework
- **OpenAI GPT** - Sun'iy intellekt
- **yt-dlp** - Video/audio yuklab olish
- **DuckDuckGo Search** - Internet qidiruv
- **aiosqlite** - Asinxron SQLite ma'lumotlar bazasi
- **python-dotenv** - Muhit o'zgaruvchilarni boshqarish

## Loyiha tuzilishi

```
Sylenth-agent/
  config.py          - Sozlamalar
  database.py        - Ma'lumotlar bazasi
  main.py            - Asosiy fayl
  requirements.txt   - Kutubxonalar
  bot/
    __init__.py
    safety.py        - Xavfsizlik filtri
    ai_engine.py     - OpenAI integratsiyasi
    search.py        - Internet qidiruv
    downloader.py    - Media yuklab olish
  handlers/
    __init__.py
    commands.py      - Buyruq handlerlari
    private.py       - Shaxsiy xabarlar
    group.py         - Guruh xabarlari
  middlewares/
    __init__.py
    throttle.py      - Anti-flood
```

## Litsenziya

MIT License
