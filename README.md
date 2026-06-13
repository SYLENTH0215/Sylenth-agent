# SYLENTH AI Agent 🤖

Telegram chatlarini avtomatlashtirish uchun eng ilg'or AI bot. OpenAI GPT modellari bilan quvvatlanadi va ko'plab funksiyalarga ega.

## 🚀 Asosiy Imkoniyatlar

### 💬 AI Suhbat
- **GPT-3.5 Turbo** orqali aqlli muloqot
- Suhbat tarixini eslab qolish
- Ko'p tillarda javob berish
- Toksik kontentni aniqlash va bloklash

### 🎨 Media Yaratish
- **Pollinations.ai Flux.1** bilan AI rasm generatsiyasi
- Tabiiy til orqali rasm yaratish
- Yuqori sifatli tasvirlar

### 📥 Media Yuklash
- YouTube, TikTok, Instagram videolarni yuklash
- MP3 formatda musiqa yuklash
- Avtomatik format konvertatsiyasi
- 45MB gacha fayl yuklash

### 🔍 Veb Qidiruv
- DuckDuckGo integratsiyasi
- Real-time internet qidirish
- To'liq natijalar bilan

### 📄 Hujjat Tahlili
- PDF fayllarni o'qish va tahlil qilish
- Rasm tahlili (GPT-4 Vision)
- Matnli hujjatlar bilan ishlash

### 👥 Guruh Boshqaruvi
- Guruhlarda avtomatik javob berish
- @mention va reply detekti
- Inline mode qo'llab-quvvatlash

### 🛡️ Admin Panel
- Foydalanuvchilar statistikasi
- Broadcast xabarlari
- Ban/Unban funksiyalari
- Database boshqaruvi
- Real-time monitoring (CPU, RAM, Disk)

### 🔐 Xavfsizlik
- Anti-flood middleware
- Obuna majburlash (opsional)
- Avtomatik ban tizimi
- Toksik kontent filtri
- API kalitlar muhofazasi

## 🛠 Texnologiyalar

- **Python 3.10+** — asosiy dasturlash tili
- **Aiogram 3.13** — Telegram bot framework
- **OpenAI API** — GPT modellari
- **yt-dlp** — media yuklab olish
- **DuckDuckGo Search** — veb qidiruv
- **SQLite3** — database
- **Pillow, PyMuPDF** — media processing

## ⚙️ O'rnatish va Ishga Tushirish

### 1. Repository'ni klonlash

```bash
git clone https://github.com/SYLENTH0215/Sylenth-agent.git
cd Sylenth-agent
```

### 2. Virtual environment yaratish

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. .env faylni sozlash

`.env` faylni yarating va quyidagi ma'lumotlarni to'ldiring:

```env
# Telegram Bot Token (t.me/BotFather orqali oling)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# OpenAI API Key (https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-...

# Admin ID (Sizning Telegram ID - @userinfobot)
ADMIN_ID=123456789

# Opsional sozlamalar
REQUIRED_CHANNEL=@your_channel
FLOOD_RATE=1.5
BAN_THRESHOLD=5
MAX_FILE_MB=45
```

### 5. Botni ishga tushirish

```bash
python main.py
```

## 📱 Foydalanish

### Asosiy Buyruqlar

- `/start` — Botni boshlash
- `/help` — Yordam ma'lumoti
- `/id` — Sizning SYLENTH ID
- `/clear` — Suhbat tarixini tozalash
- `/draw tavsif` — AI rasm yaratish
- `/music qo'shiq` — MP3 yuklash

### Admin Buyruqlari

- `/ceo` — Admin panel
- `/ban <tg_id> [sabab]` — Foydalanuvchini bloklash
- `/unban <tg_id>` — Blokdan chiqarish

### Rejimlar

Bot 5 xil rejimda ishlaydi:

1. **💬 Suhbat** — Oddiy AI suhbat
2. **🧠 Chuqur tahlil** — Batafsil javoblar
3. **🔍 Qidiruv** — Internet qidirish
4. **🎨 Rasm yaratish** — AI generatsiya
5. **📥 Media yuklash** — Video/Audio yuklash

### Media Ishlatish

- **Rasm yuborish** → AI tahlil qiladi
- **PDF yuborish** → Matnni o'qib javob beradi
- **Video link** → Yuklab beradi

## 🤖 GitHub Actions (24/7 Ishlash)

Bot GitHub Actions orqali uzluksiz ishlay oladi:

### 1. Repository Settings
- Settings → Secrets and variables → Actions
- Quyidagi secretlarni qo'shing:
  - `BOT_TOKEN`
  - `OPENAI_API_KEY`
  - `ADMIN_ID`

### 2. Workflow fayl

`.github/workflows/main.yml` fayli allaqachon mavjud.

### 3. Actions ni yoqish

- Repository → Actions → Enable workflows
- Workflow avtomatik ishga tushadi

## 📊 Statistika va Monitoring

Admin panel orqali quyidagilarni ko'rish mumkin:

- Jami foydalanuvchilar
- Bugungi qo'shilganlar  
- Faol foydalanuvchilar (24s)
- Banlangan foydalanuvchilar
- Guruhlar soni
- Xabarlar soni
- Tizim resurslari (CPU, RAM, Disk)

## 🔧 Xatoliklarni Bartaraf Qilish

### Bot ishga tushmayapti

```bash
# Python versiyasini tekshiring
python --version  # 3.10+ bo'lishi kerak

# Kutubxonalarni qayta o'rnating
pip install --upgrade -r requirements.txt
```

### OpenAI API xatosi

- API kalitingiz to'g'riligini tekshiring
- Hisobingizda kredit borligini tasdiqlang
- API limitlaringizni tekshiring

### Video yuklab olish ishlamayapti

```bash
# FFmpeg o'rnatish (Linux)
sudo apt install ffmpeg

# FFmpeg o'rnatish (Mac)
brew install ffmpeg

# FFmpeg o'rnatish (Windows)
# https://ffmpeg.org/download.html dan yuklab oling
```

## 📝 Litsenziya

MIT License - bepul foydalanish va o'zgartirish mumkin.

## 👨‍💻 Muallif

**Zayniddinov Davron** — SYLENTH jamoasi
- Telegram: [@sylenth_uz](https://t.me/sylenth_uz)
- GitHub: [@SYLENTH0215](https://github.com/SYLENTH0215)

## 🤝 Hissa qo'shish

Pull requestlar va xato xabarlari xush kelibsiz!

1. Fork qiling
2. Feature branch yarating (`git checkout -b feature/amazing`)
3. Commit qiling (`git commit -m 'Add amazing feature'`)
4. Push qiling (`git push origin feature/amazing`)
5. Pull Request oching

## ⭐ Yoqtirish

Agar loyiha yoqqan bo'lsa, ⭐ star bering!

---

**🔥 SYLENTH Agent — Eng zamonaviy AI bot!**
