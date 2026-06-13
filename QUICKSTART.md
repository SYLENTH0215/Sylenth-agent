# 🚀 SYLENTH Agent - Tezkor Boshlash

## 5 Daqiqada Ishga Tushiring!

### 1. Repository'ni oling
```bash
git clone https://github.com/SYLENTH0215/Sylenth-agent.git
cd Sylenth-agent
```

### 2. API kalitlarni oling

- **BOT_TOKEN**: [@BotFather](https://t.me/BotFather) → `/newbot`
- **OPENAI_API_KEY**: [platform.openai.com](https://platform.openai.com/api-keys)
- **ADMIN_ID**: [@userinfobot](https://t.me/userinfobot)

### 3. .env yarating
```bash
cp .env.example .env
nano .env  # Kalitlarni kiriting
```

### 4. Ishga tushiring

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 5. Test qiling
```bash
python test_bot.py
```

## ✅ Tayyor!

Bot Telegram'da ishlaydi. `/start` yuboring!

---

**Batafsil:** [SETUP.md](SETUP.md)  
**Dokumentatsiya:** [README.md](README.md)  
**API:** [API.md](API.md)
