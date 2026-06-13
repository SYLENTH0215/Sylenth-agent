# SYLENTH Agent - API Dokumentatsiyasi

## Bot Arxitekturasi

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│              (Bot & Dispatcher)                     │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌───────▼────────┐
│  Middlewares   │   │    Handlers    │
│                │   │                │
│ • AntiFlood    │   │ • Commands     │
│ • Access       │   │ • Messages     │
└────────────────┘   │ • Media        │
                     │ • CEO          │
                     │ • Group        │
                     └───────┬────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
            ┌───────▼───────┐  ┌──────▼──────┐
            │  AI Engine    │  │  Database   │
            │               │  │             │
            │ • OpenAI GPT  │  │ • SQLite3   │
            │ • Toxicity    │  │ • Users     │
            └───────────────┘  │ • Messages  │
                               │ • Groups    │
                               └─────────────┘
```

## Modullar

### 1. main.py
**Vazifa:** Bot entry point va konfiguratsiya

**Asosiy funksiyalar:**
```python
async def on_startup()
    # Bot ishga tushishdan oldin
    # - downloads papkasi yaratish
    # - database inicializatsiya
    # - logging sozlash

async def main()
    # Asosiy bot loop
    # - webhook o'chirish
    # - polling boshlash
```

**Middleware tartibi:**
1. AntiFloodMiddleware (spam himoya)
2. AccessMiddleware (ban tekshirish, obuna majburlash)

**Router tartibi:**
1. commands (buyruqlar)
2. ceo (admin panel)
3. group (guruh boshqaruvi)
4. media (media yuklab olish)
5. messages (xabarlarni qayta ishlash)

---

### 2. config.py
**Vazifa:** Environment o'zgaruvchilarni yuklash

**Ekspоrt qilinadigan o'zgaruvchilar:**
```python
BOT_TOKEN: str          # Telegram bot token
ADMIN_ID: int           # Admin foydalanuvchi ID
REQUIRED_CHANNEL: str   # Majburiy kanal (opsional)
OPENAI_API_KEY: str     # OpenAI API kaliti
GROQ_KEY: str          # Groq API kaliti (opsional)
PROJECT_NAME: str      # Loyiha nomi
FLOOD_RATE: float      # Anti-flood vaqt oralig'i
BAN_THRESHOLD: int     # Avtomatik ban limiti
MAX_FILE_MB: int       # Maksimal fayl hajmi
DOWNLOADS_DIR: str     # Yuklab olish papkasi
```

---

### 3. database.py
**Vazifa:** SQLite database bilan ishlash

#### 3.1. Tables

**users:**
```sql
sylenth_id   INTEGER PRIMARY KEY   -- Ichki ID
tg_id        INTEGER UNIQUE        -- Telegram ID
username     TEXT                  -- @username
full_name    TEXT                  -- To'liq ism
is_banned    INTEGER (0/1)         -- Ban holati
warn_count   INTEGER               -- Ogohlantirish soni
mode         TEXT                  -- Joriy rejim
joined_at    TEXT (datetime)       -- Qo'shilgan vaqt
last_active  TEXT (datetime)       -- Oxirgi faollik
msg_count    INTEGER               -- Xabarlar soni
```

**groups:**
```sql
chat_id   INTEGER PRIMARY KEY   -- Guruh chat ID
title     TEXT                  -- Guruh nomi
added_at  TEXT (datetime)       -- Qo'shilgan vaqt
```

**messages:**
```sql
id         INTEGER PRIMARY KEY AUTOINCREMENT
chat_id    INTEGER              -- Chat ID
tg_id      INTEGER              -- Foydalanuvchi ID
role       TEXT                 -- "user" yoki "model"
content    TEXT                 -- Xabar matni
created_at TEXT (datetime)      -- Yaratilgan vaqt
```

**blacklist:**
```sql
tg_id      INTEGER PRIMARY KEY  -- Telegram ID
reason     TEXT                 -- Ban sababi
banned_at  TEXT (datetime)      -- Ban vaqti
```

#### 3.2. Functions

```python
init_db() -> None
    # Database va tablelarni yaratish

get_or_create_user(tg_id, username, full_name) -> dict
    # Foydalanuvchi olish yoki yangi yaratish
    # Returns: {"sylenth_id", "tg_id", "mode", "msg_count"}

get_user(tg_id) -> dict | None
    # Foydalanuvchi ma'lumotlari
    # Returns: {"sylenth_id", "msg_count", "is_banned", "joined_at"}

is_banned(tg_id) -> bool
    # Ban tekshirish

warn_user(tg_id) -> int
    # Ogohlantirish qo'shish
    # Returns: jami ogohlantirish soni

ban_user(tg_id, reason)
    # Foydalanuvchini ban qilish

unban_user(tg_id)
    # Ban dan chiqarish

increment_msg_count(tg_id)
    # Xabar sonini oshirish

clear_history(chat_id)
    # Suhbat tarixini tozalash

save_group(chat_id, title)
    # Guruhni saqlash

save_message(chat_id, tg_id, role, content)
    # Xabarni saqlash

get_history(chat_id, limit=10) -> list[dict]
    # Suhbat tarixini olish
    # Returns: [{"role", "parts": [content]}]

get_stats() -> dict
    # Statistika
    # Returns: {"total", "today", "active", "banned", "groups", "messages"}

get_all_user_ids() -> list[int]
    # Barcha user ID lar

get_all_group_ids() -> list[int]
    # Barcha group ID lar

get_recent_users(limit=10) -> list[dict]
    # So'nggi foydalanuvchilar
```

---

### 4. ai_engine.py
**Vazifa:** AI modellari bilan ishlash

#### 4.1. OpenAI Client

```python
client = OpenAI(api_key=OPENAI_API_KEY)
```

#### 4.2. System Prompt

```python
SYSTEM_PROMPT = """
Sen SYLENTH Agent — SYLENTH jamoasi tomonidan 
yaratilgan sun'iy intellekt yordamchisan.

QOIDALAR:
1. Do'stona va xurmatli javob berish
2. Har qanday tilda javob berish
3. Texnik savollarga to'liq ma'lumot
4. Tiq, odobsiz mavzularda javob berma
5. Bilmasang - aytib ber
"""
```

#### 4.3. Functions

```python
is_toxic(text: str) -> bool
    # Toksik matn tekshirish
    # Taqiqlangan so'zlar: so'kin, haqorat, porn, kill, etc.

async ask_ai(user_text, history=None, **kwargs) -> str
    # GPT-3.5-turbo orqali javob
    # Parameters:
    #   - user_text: foydalanuvchi xabari
    #   - history: suhbat tarixi (list[dict])
    # Returns: AI javob matni

async analyze_image(image_bytes, prompt="") -> str
    # GPT-4 Vision bilan rasm tahlili
    # Parameters:
    #   - image_bytes: rasm (bytes)
    #   - prompt: tahlil uchun savol
    # Returns: tahlil natijasi

async deep_think(user_text, history=None, **kwargs) -> str
    # Chuqur tahlil (enhanced prompt)
    # ask_ai ga qaraganda batafsilroq

async ask_gemini(user_text, history=None, **kwargs) -> str
    # Gemini API (hozirda ask_ai chaqiradi)
```

---

### 5. utils.py
**Vazifa:** Yordamchi funksiyalar

```python
web_search(query: str) -> str
    # DuckDuckGo qidiruv
    # Returns: HTML formatda natijalar

get_image_url(prompt: str) -> str
    # Pollinations.ai Flux.1 rasm URL
    # Returns: rasm havolasi

extract_pdf_text(pdf_bytes: bytes) -> str
    # PDF dan matn chiqarish (PyMuPDF)
    # Returns: matn (birinchi 12000 belgi)

safe_remove(path: str)
    # Faylni xavfsiz o'chirish

file_size_mb(path: str) -> float
    # Fayl hajmi (MB)

async download_video(url: str) -> tuple[str|None, str]
    # YouTube/TikTok/Instagram video yuklash
    # Returns: (file_path, title) yoki (None, error)

async download_audio(query: str) -> tuple[str|None, dict]
    # YouTube'dan MP3 yuklash
    # Returns: (file_path, metadata) yoki (None, {"error": msg})
```

---

### 6. states.py
**Vazifa:** FSM holatlarini belgilash

```python
class UserMode(StatesGroup):
    chat   = State()    # Oddiy suhbat
    draw   = State()    # Rasm yaratish
    search = State()    # Veb qidiruv
    think  = State()    # Chuqur tahlil
    dl     = State()    # Media yuklash

class CEOState(StatesGroup):
    broadcast = State()  # Broadcast yozish
    ban_input = State()  # Ban ma'lumotlari
```

---

### 7. keyboards.py
**Vazifa:** Inline klaviaturalar

```python
main_menu() -> InlineKeyboardMarkup
    # Asosiy menyu
    # Tugmalar: Draw, Search, Think, Download, Chat, ID, Help

ceo_panel() -> InlineKeyboardMarkup
    # Admin panel
    # Tugmalar: Stats, Users, Broadcast, Ban, Unban, ClearDB

subscribe_btn(channel: str) -> InlineKeyboardMarkup
    # Obuna tugmasi
    # Tugmalar: Subscribe, Check

cancel_btn() -> InlineKeyboardMarkup
    # Bekor qilish tugmasi
```

---

## Handlers

### 8. handlers/commands.py
**Buyruqlar handleri**

| Buyruq | Tavsif | Handler |
|--------|--------|---------|
| `/start` | Botni boshlash | `cmd_start` |
| `/help` | Yordam | `cmd_help` |
| `/clear` | Tarixni tozalash | `cmd_clear` |
| `/id` | SYLENTH ID | `cmd_id` |
| `/draw` | Rasm yaratish | `cmd_draw` |
| `/music` | MP3 yuklash | `cmd_music` |
| `/ban` | Ban qilish (admin) | `cmd_ban` |
| `/unban` | Ban dan chiqarish (admin) | `cmd_unban` |
| `/ceo` | Admin panel (admin) | `cmd_ceo` |

**Callback Queries:**
- `check_sub` - Obuna tekshirish

---

### 9. handlers/messages.py
**Xabarlar handleri**

**Text xabarlar (FSM holatiga qarab):**

| Holat | Handler | Vazifa |
|-------|---------|--------|
| `UserMode.chat` | `handle_chat` | Oddiy AI suhbat |
| `UserMode.think` | `handle_think` | Chuqur tahlil |
| `UserMode.search` | `handle_search` | Veb qidiruv |
| `UserMode.draw` | `handle_draw` | Rasm yaratish |
| `UserMode.dl` | `handle_dl` | Media yuklash |

**Media:**
- `F.photo` → `handle_photo` - Rasm tahlili
- `F.document` → `handle_document` - PDF tahlili

**Callback Queries:**
- `mode_chat` - Chat rejimini yoqish
- `mode_think` - Think rejimini yoqish
- `mode_search` - Search rejimini yoqish
- `mode_draw` - Draw rejimini yoqish
- `mode_dl` - Download rejimini yoqish
- `my_id` - Foydalanuvchi ma'lumoti
- `help` - Yordam
- `back_main` - Asosiy menyuga qaytish
- `cancel` - Bekor qilish

---

### 10. handlers/media.py
**Media handleri**

```python
async send_image(message, prompt: str)
    # Pollinations.ai orqali rasm yuborish

async download_and_send_music(message, query: str)
    # YouTube'dan MP3 yuklab yuborish

async smart_download(message, url: str)
    # Video/Audio aqlli yuklash
    # YouTube, TikTok, Instagram, X, Facebook
```

---

### 11. handlers/ceo.py
**Admin panel handleri**

**Callback Queries:**

| Callback | Handler | Vazifa |
|----------|---------|--------|
| `ceo_stats` | `ceo_stats` | Statistika ko'rsatish |
| `ceo_users` | `ceo_users` | So'nggi foydalanuvchilar |
| `ceo_broadcast` | `ceo_broadcast_start` | Broadcast boshlash |
| `ceo_ban` | `ceo_ban_start` | Ban qilish boshlash |
| `ceo_unban` | `ceo_unban` | Unban ko'rsatmasi |
| `ceo_cleardb` | `ceo_cleardb` | Database tozalash |
| `back_main` | `back_main` | Asosiy menyuga qaytish |

**States:**
- `CEOState.broadcast` + Message → `ceo_broadcast_send`
- `CEOState.ban_input` + Message → `ceo_ban_execute`

---

### 12. handlers/group.py
**Guruh handleri**

```python
@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def bot_added(event)
    # Bot guruhga qo'shilganda xabar

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group(message, bot)
    # Guruhda mention/reply orqali javob berish

@router.inline_query()
async def inline_handler(query)
    # @bot_username inline rejimi
    # Natijalar: AI javob, Rasm, Qidiruv
```

---

## Middlewares

### 13. middlewares/anti_flood.py
**Spam himoyasi**

```python
class AntiFloodMiddleware(BaseMiddleware):
    # Algorit:
    # 1. Oxirgi xabar vaqtini tekshirish
    # 2. Agar FLOOD_RATE dan kam bo'lsa → ogohlantirish
    # 3. BAN_THRESHOLD ga yetsa → avtomatik ban
    # 4. Admin'ga taalluqli emas
```

---

### 14. middlewares/access.py
**Kirish nazorati**

```python
class AccessMiddleware(BaseMiddleware):
    # Algorit:
    # 1. Foydalanuvchini yaratish/olish
    # 2. Ban tekshirish → bloklash
    # 3. REQUIRED_CHANNEL tekshirish → obuna majburlash
    # 4. Admin'ga taalluqli emas
```

---

## Flow Diagramma

### Xabar qayta ishlash jarayoni:

```
User xabar → Aiogram
     │
     ▼
AntiFloodMiddleware
     │ (spam tekshirish)
     ▼
AccessMiddleware
     │ (ban, obuna tekshirish)
     ▼
Router (commands → ceo → group → media → messages)
     │
     ▼
Handler (state'ga qarab)
     │
     ├─→ AI Engine (OpenAI API)
     ├─→ Utils (media, search)
     └─→ Database (save/load)
     │
     ▼
Response → User
```

---

## API Rate Limits

### OpenAI API
- GPT-3.5-turbo: 3 RPM (Free tier)
- GPT-4-vision: 3 RPM (Free tier)
- Kredit tugasa → xato

### DuckDuckGo
- Rate limit yo'q
- Proxy talab qilinmaydi

### Pollinations.ai
- Rate limit yo'q
- Bepul

### YouTube (yt-dlp)
- IP bo'yicha limit
- Proxy kerak bo'lishi mumkin

---

## Environment Variables

| O'zgaruvchi | Majburiy | Default | Tavsif |
|-------------|----------|---------|--------|
| `BOT_TOKEN` | ✅ | - | Telegram bot token |
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `ADMIN_ID` | ✅ | 0 | Admin Telegram ID |
| `REQUIRED_CHANNEL` | ❌ | "" | Obuna kanal |
| `GROQ_KEY` | ❌ | "" | Groq API key |
| `FLOOD_RATE` | ❌ | 1.5 | Anti-flood vaqt (s) |
| `BAN_THRESHOLD` | ❌ | 5 | Avtomatik ban limit |
| `MAX_FILE_MB` | ❌ | 45 | Maksimal fayl hajmi |
| `DOWNLOADS_DIR` | ❌ | downloads | Yuklab olish papkasi |

---

## Error Handling

### Xatolar va ularga javoblar:

| Xato | Sabab | Yechim |
|------|-------|--------|
| `ValueError: BOT_TOKEN muhim!` | Token yo'q | .env da `BOT_TOKEN` qo'shing |
| `Invalid API key` | Noto'g'ri OpenAI key | API key tekshiring |
| `Rate limit exceeded` | OpenAI limit | Biroz kuting |
| `Insufficient credits` | OpenAI kredit tugagan | Kredit qo'shing |
| `Chat not found` | Kanal ID noto'g'ri | `REQUIRED_CHANNEL` tekshiring |
| `FFmpeg not found` | FFmpeg o'rnatilmagan | `apt install ffmpeg` |

---

## Testing

### Unit test misollari:

```python
# test_database.py
def test_get_or_create_user():
    user = get_or_create_user(12345, "test", "Test User")
    assert user["tg_id"] == 12345
    assert user["mode"] == "chat"

# test_ai_engine.py
def test_is_toxic():
    assert is_toxic("kill") == True
    assert is_toxic("salom") == False

# test_utils.py
def test_get_image_url():
    url = get_image_url("test prompt")
    assert "pollinations.ai" in url
```

---

## Performance Tips

1. **Database indekslar:**
   ```sql
   CREATE INDEX idx_tg_id ON users(tg_id);
   CREATE INDEX idx_chat_id ON messages(chat_id);
   ```

2. **Cache qo'shish:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_user(tg_id):
       # ...
   ```

3. **Async optimization:**
   ```python
   # Parallel API calls
   results = await asyncio.gather(
       ask_ai(text1),
       ask_ai(text2)
   )
   ```

---

## Security Best Practices

1. **.env faylni .gitignore ga qo'shing**
2. **API kalitlarni hech qachon commit qilmang**
3. **ADMIN_ID ni .env da saqlang**
4. **Database faylini backup qiling**
5. **Rate limiting qo'shing**
6. **Input validation qiling**

---

## Changelog

### v1.0.0 (2024)
- ✅ OpenAI GPT-3.5 integratsiyasi
- ✅ Rasm generatsiyasi (Flux.1)
- ✅ Media yuklash (yt-dlp)
- ✅ Veb qidiruv (DuckDuckGo)
- ✅ Admin panel
- ✅ Anti-flood va access control
- ✅ SQLite database
- ✅ Guruh boshqaruvi
- ✅ Inline mode
- ✅ PDF tahlili
- ✅ Rasm tahlili (GPT-4 Vision)

---

**API documentation by SYLENTH Team**
