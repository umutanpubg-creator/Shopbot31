from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import json
import os

TOKEN = "8488632483:AAGKfrEOg5_Q29ukG0Genl_lS5WicRNLKro"  # <-- Bot tokenini buraya koy
ADMIN_ID = 7279061074       # <-- Kendi Telegram ID'n
URUNLER_FILE = "urunler.json"

# JSON okuma/yazma
def urunleri_oku():
    if not os.path.exists(URUNLER_FILE):
        return []
    with open(URUNLER_FILE, "r") as f:
        return json.load(f)

def urunleri_yaz(data):
    with open(URUNLER_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ----------------- Admin Panel -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        await update.message.reply_text("Merhaba Admin! /panel ile paneli açabilirsin.")
    else:
        urunler = urunleri_oku()
        bolumler = sorted(list(set(u["bolum"] for u in urunler)))
        keyboard = []
        for b in bolumler:
            keyboard.append([InlineKeyboardButton(b, callback_data=f"user_bolum::{b}")])
        await update.message.reply_text("Bölümler:", reply_markup=InlineKeyboardMarkup(keyboard))

# /panel komutu
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Yetkin yok.")
        return
    urunler = urunleri_oku()
    bolumler = sorted(list(set(u["bolum"] for u in urunler)))
    keyboard = []
    for b in bolumler:
        keyboard.append([InlineKeyboardButton(b, callback_data=f"bolum::{b}")])
    keyboard.append([InlineKeyboardButton("➕ Bölüm Ekle", callback_data="bolum_ekle")])
    keyboard.append([InlineKeyboardButton("❌ Bölüm Sil", callback_data="bolum_sil")])
    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# Admin callback handler
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    urunler = urunleri_oku()

    # Bölüm seçimi
    if data.startswith("bolum::"):
        bolum = data.split("::",1)[1]
        keyboard = []
        for u in [x for x in urunler if x["bolum"]==bolum]:
            keyboard.append([InlineKeyboardButton(f"{u['isim']} ({u['fiyat']}) 🗑️", callback_data=f"delete_urun::{bolum}::{u['isim']}")])
        keyboard.append([InlineKeyboardButton("➕ Ürün Ekle", callback_data=f"add_urun::{bolum}")])
        keyboard.append([InlineKeyboardButton("🔙 Panel", callback_data="panel")])
        await query.edit_message_text(f"📂 {bolum} Bölümü", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Panel geri
    if data=="panel":
        await panel(update, context)
        return

    # Bölüm ekle
    if data=="bolum_ekle":
        context.user_data["adding_bolum"] = True
        await query.edit_message_text("Yeni bölüm adı gönder:")
        return

    # Bölüm sil
    if data=="bolum_sil":
        keyboard = []
        bolumler = sorted(list(set(u["bolum"] for u in urunler)))
        for b in bolumler:
            keyboard.append([InlineKeyboardButton(f"{b} ❌", callback_data=f"delete_bolum::{b}")])
        keyboard.append([InlineKeyboardButton("🔙 Panel", callback_data="panel")])
        await query.edit_message_text("Hangi bölümü silmek istiyorsun?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Bölüm silme işlemi
    if data.startswith("delete_bolum::"):
        bolum = data.split("::",1)[1]
        urunler = [u for u in urunler if u["bolum"]!=bolum]
        urunleri_yaz(urunler)
        await query.edit_message_text(f"✅ '{bolum}' bölümü ve içindeki ürünler silindi.")
        return

    # Ürün ekle
    if data.startswith("add_urun::"):
        bolum = data.split("::",1)[1]
        context.user_data["adding_urun"] = bolum
        await query.edit_message_text("Ürünü gönder (isim;fiyat):")
        return

    # Ürün sil
    if data.startswith("delete_urun::"):
        bolum, isim = data.split("::")[1:]
        urunler = [u for u in urunler if not (u["bolum"]==bolum and u["isim"]==isim)]
        urunleri_yaz(urunler)
        await query.edit_message_text(f"✅ '{isim}' silindi.")
        return

# Mesajla ekleme işlemleri
async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    urunler = urunleri_oku()

    # Admin işlemleri
    if user.id == ADMIN_ID:
        # Bölüm ekleme
        if context.user_data.get("adding_bolum"):
            context.user_data["adding_bolum"] = False
            urunler.append({"bolum": text, "isim": "Örnek Ürün", "fiyat": 0})
            urunleri_yaz(urunler)
            await update.message.reply_text(f"✅ '{text}' bölümü eklendi (örnek ürün ile).")
            return

        # Ürün ekleme
        if "adding_urun" in context.user_data:
            bolum = context.user_data.pop("adding_urun")
            try:
                isim, fiyat = text.split(";")
                fiyat = float(fiyat)
                urunler.append({"bolum": bolum, "isim": isim.strip(), "fiyat": fiyat})
                urunleri_yaz(urunler)
                await update.message.reply_text(f"✅ '{isim.strip()}' ürünü eklendi. Fiyat: {fiyat}")
            except:
                await update.message.reply_text("❌ Hatalı format. Örn: ÜrünAdı;Fiyat")
        return

# ----------------- Kullanıcı Paneli -----------------

async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    urunler = urunleri_oku()

    if data.startswith("user_bolum::"):
        bolum = data.split("::",1)[1]
        keyboard = []
        for u in [x for x in urunler if x["bolum"]==bolum]:
            keyboard.append([InlineKeyboardButton(f"{u['isim']} ({u['fiyat']})", callback_data=f"buy::{u['isim']}::{u['fiyat']}")])
        await query.edit_message_text(f"{bolum} ürünleri:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("buy::"):
        isim, fiyat = data.split("::")[1:]
        # Admina mesaj gönder
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🛒 Kullanıcı @{query.from_user.username} ürün almak istiyor: {isim} ({fiyat})")
        await query.edit_message_text(f"✅ Sipariş isteğiniz gönderildi: {isim} ({fiyat})")
        return

# ----------------- Bot Başlat -----------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CallbackQueryHandler(callback, pattern=r'^(bolum|delete|add|panel)_'))
app.add_handler(CallbackQueryHandler(user_callback, pattern=r'^user_'))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mesaj))

print("Bot çalışıyor...")
app.run_polling()