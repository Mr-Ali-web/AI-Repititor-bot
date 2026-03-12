#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ConversationHandler
)
import google.generativeai as genai 

import asyncio
import sys
import nest_asyncio

# Windows uchun maxsus sozlash
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Mavjud event loop ga patch qo'llash
nest_asyncio.apply()


# LOGGING
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

print("🚀 Dastur ishga tushyapti...")

# --- TO'G'RI TOKENLAR (RENDERDAGI BILAN BIR XIL) ---
TELEGRAM_TOKEN = "8665590507:AAEXHhP6_Blv8Ocikc9YCapV4w6nJk51Ni8"  # TO'G'RI TOKEN
GEMINI_API_KEY = "AIzaSyBKtSKNCf3dB2FOj1MEIXRNNAF6hwV8PSQ"  # RENDERDAGI GEMINI_API_KEY

# Gemini sozlamasi
genai.configure(api_key=GEMINI_API_KEY)

# MA'LUMOTLAR BAZASI
USERS_FILE = 'users.json'

def load_db():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: 
            return {}
    return {}

def save_db(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

users_db = load_db()

# CONVERSATION STATES
NAME, CLASS, SUBJECTS, PHONE, PARENT_PHONE = range(5)
SUBJECTS_LIST = {'1': '📐 Matematika', '2': '⚛️ Fizika', '3': '🧪 Kimyo', '4': '🧬 Biologiya', '5': '📜 Tarix', '6': '🇬🇧 Ingliz tili'}

# FLASK APP
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti! 🚀"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    return "OK", 200

# UI TUGMALAR
def get_main_menu():
    keyboard = [
        [KeyboardButton("🤖 AI Repetitor"), KeyboardButton("🎮 Bilim O'yini")],
        [KeyboardButton("📊 Reyting"), KeyboardButton("👤 Profilim")],
        [KeyboardButton("ℹ️ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_gemini_response(prompt):
    """Gemini API dan javob olish"""
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return None

# START HANDLER
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in users_db:
        await update.message.reply_text(
            f"Xush kelibsiz, {users_db[user_id].get('name', 'Foydalanuvchi')}!",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Assalomu alaykum! Botdan foydalanish uchun ro'yxatdan o'ting.\n"
        "Ism va familiyangizni kiriting:"
    )
    return NAME

# REGISTRATION HANDLERS
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Sinfingizni kiriting (masalan: 9-B):")
    return CLASS

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['class'] = update.message.text
    context.user_data['subs'] = []
    
    keyboard = [[InlineKeyboardButton(v, callback_data=f"sub_{k}")] for k, v in SUBJECTS_LIST.items()]
    keyboard.append([InlineKeyboardButton("✅ Tanlab bo'ldim", callback_data="sub_done")])
    
    await update.message.reply_text(
        "O'zingiz qiziqqan fanlarni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SUBJECTS

async def select_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sub_done":
        if not context.user_data.get('subs'):
            await query.message.reply_text("Kamida bitta fan tanlang!")
            return SUBJECTS
        
        await query.message.reply_text(
            "Telefon raqamingizni yuboring (masalan: +998901234567):"
        )
        return PHONE
    
    sub_id = query.data.split('_')[1]
    sub_name = SUBJECTS_LIST[sub_id]
    
    if sub_name not in context.user_data['subs']:
        context.user_data['subs'].append(sub_name)
    
    selected = ", ".join(context.user_data['subs'])
    await query.edit_message_text(
        f"Tanlangan fanlar: {selected}\n\nYana tanlashni davom ettirishingiz mumkin:",
        reply_markup=query.message.reply_markup
    )
    return SUBJECTS

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if not phone.replace('+', '').replace('-', '').isdigit():
        await update.message.reply_text("Iltimos, to'g'ri telefon raqam kiriting:")
        return PHONE
        
    context.user_data['phone'] = phone
    await update.message.reply_text("Ota-onangizning telefon raqamini kiriting:")
    return PARENT_PHONE

async def get_parent_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parent_phone = update.message.text
    
    user_id = str(update.effective_user.id)
    users_db[user_id] = {
        'name': context.user_data['name'],
        'class': context.user_data['class'],
        'subjects': context.user_data['subs'],
        'phone': context.user_data['phone'],
        'parent_phone': parent_phone,
        'points': 0,
        'history': 0,
        'ai_mode': False
    }
    save_db(users_db)
    
    await update.message.reply_text(
        "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

# AI CHAT HANDLER
async def ai_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in users_db:
        await update.message.reply_text("Avval ro'yxatdan o'ting! /start")
        return
    
    users_db[user_id]['ai_mode'] = True
    save_db(users_db)
    
    await update.message.reply_text(
        "🤖 AI Repetitor rejimi yoqildi!\n"
        "Savolingizni yozing (AI dan chiqish uchun /exit yozing):"
    )

async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if user_id not in users_db or not users_db[user_id].get('ai_mode', False):
        return
    
    if text.lower() == '/exit':
        users_db[user_id]['ai_mode'] = False
        save_db(users_db)
        await update.message.reply_text(
            "AI Repetitor rejimidan chiqildi.",
            reply_markup=get_main_menu()
        )
        return
    
    waiting_msg = await update.message.reply_text("⏳ AI javob tayyorlamoqda...")
    
    try:
        user_data = users_db[user_id]
        
        prompt = f"""Sen o'quvchilarga yordam beruvchi AI repetitorsan. 
O'quvchi haqida ma'lumot:
- Ismi: {user_data.get('name')}
- Sinf: {user_data.get('class')}
- Qiziqish fanlari: {', '.join(user_data.get('subjects', []))}

O'quvchining savoli: {text}

Iltimos, oddiy va tushunarli tilda, batafsil javob ber. O'zbek tilida javob ber."""
        
        response_text = get_gemini_response(prompt)
        
        if response_text:
            users_db[user_id]['points'] = users_db[user_id].get('points', 0) + 5
            users_db[user_id]['history'] = users_db[user_id].get('history', 0) + 1
            save_db(users_db)
            
            if len(response_text) > 4000:
                parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
                await update.message.reply_text("✅ +5 ball berildi!")
                await waiting_msg.delete()
            else:
                await waiting_msg.edit_text(
                    f"{response_text}\n\n✅ +5 ball berildi!"
                )
        else:
            await waiting_msg.edit_text(
                "❌ AI bilan bog'lanishda xato yuz berdi.\n"
                "Qaytadan urinib ko'ring yoki /exit yozib chiqing."
            )
        
    except Exception as e:
        logger.error(f"AI Xatosi: {e}")
        await waiting_msg.edit_text(
            "❌ AI bilan bog'lanishda xato yuz berdi.\n"
            f"Xato: {str(e)[:100]}..."
        )

# PROFILE HANDLER
async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in users_db:
        await update.message.reply_text("Avval ro'yxatdan o'ting! /start")
        return
    
    user_data = users_db[user_id]
    
    subjects = user_data.get('subjects', [])
    subjects_text = ', '.join(subjects) if subjects else "Tanlanmagan"
    
    msg = (
        f"👤 **ISMI:** {user_data.get('name', 'Noma\'lum')}\n"
        f"🎓 **SINF:** {user_data.get('class', 'Noma\'lum')}\n"
        f"📚 **FANLAR:** {subjects_text}\n"
        f"⭐ **BALL:** {user_data.get('points', 0)}\n"
        f"📊 **SAVOLLAR:** {user_data.get('history', 0)}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# RATING HANDLER
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not users_db:
            await update.message.reply_text("📊 Hali hech qanday ma'lumot yo'q.")
            return
        
        sorted_users = sorted(
            users_db.values(), 
            key=lambda x: x.get('points', 0), 
            reverse=True
        )[:10]
        
        if not sorted_users:
            await update.message.reply_text("📊 Reyting bo'sh.")
            return
        
        res = "🏆 **TOP 10 O'QUVCHILAR:**\n\n"
        
        for i, user in enumerate(sorted_users, 1):
            name = user.get('name', "Noma'lum foydalanuvchi")
            points = user.get('points', 0)
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
            res += f"{medal} {i}. {name} - {points} ball\n"
        
        total_users = len(users_db)
        total_questions = sum(u.get('history', 0) for u in users_db.values())
        
        res += f"\n📊 **Umumiy statistika:**\n"
        res += f"👥 Foydalanuvchilar: {total_users}\n"
        res += f"❓ Javoblar: {total_questions}"
        
        await update.message.reply_text(res, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Reyting ko'rsatishda xato: {e}")
        await update.message.reply_text("❌ Reytingni yuklashda xato yuz berdi.")

# HELP HANDLER
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Bot buyruqlari:**

/start - Botni qayta ishga tushirish
/exit - AI rejimidan chiqish

**Tugmalar:**
• 🤖 AI Repetitor - Savol berish
• 📊 Reyting - Eng yaxshi o'quvchilar
• 👤 Profilim - Shaxsiy ma'lumotlar
• ℹ️ Yordam - Bu xabar
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# MAIN MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if user_id not in users_db:
        await update.message.reply_text("Iltimos, avval /start orqali ro'yxatdan o'ting!")
        return
    
    if text == "🤖 AI Repetitor":
        await ai_chat_start(update, context)
    
    elif text == "👤 Profilim":
        await handle_profile(update, context)
    
    elif text == "📊 Reyting":
        await handle_rating(update, context)
    
    elif text == "ℹ️ Yordam":
        await handle_help(update, context)
    
    elif text == "🎮 Bilim O'yini":
        await update.message.reply_text("🎮 Bu funksiya hozircha ishlab chiqilmoqda...")
    
    else:
        if users_db[user_id].get('ai_mode', False):
            await ai_chat_handler(update, context)
        else:
            await update.message.reply_text(
                "Nima qilmoqchisiz? Tugmalardan foydalaning.",
                reply_markup=get_main_menu()
            )

def run_bot():
    """Botni threadda ishga tushirish"""
    try:
        print("🤖 Bot threadi ishga tushyapti...")
        bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        registration_conv = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
                SUBJECTS: [CallbackQueryHandler(select_subjects)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                PARENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_parent_phone)],
            },
            fallbacks=[CommandHandler('start', start)]
        )
        
        bot_app.add_handler(registration_conv)
        bot_app.add_handler(CommandHandler('exit', ai_chat_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Bot handlerlar qo'shildi, polling boshlanmoqda...")
        bot_app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Bot threadida xatolik: {e}")
        print(f"❌ Bot xatosi: {e}")

# ASOSIY QISM
if __name__ == "__main__":
    print("🚀 MAIN: Dastur ishga tushmoqda...")
    
    # Botni threadda ishga tushirish
    print("🤖 Bot threadini yaratish...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Bot threadi boshlandi!")
    
    # Flask serverni ishga tushirish
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Flask server http://0.0.0.0:{port} da ishga tushadi")
    
    # MUHIM: debug=False bo'lishi kerak!python bot.py
    app.run(host="0.0.0.0", port=port, debug=False)