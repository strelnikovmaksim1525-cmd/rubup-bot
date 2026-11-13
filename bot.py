import logging
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Берем токен из переменных окружения Render (или впиши свой прямо в кавычки)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ЕСЛИ_НЕ_ИСПОЛЬЗУЕШЬ_RENDER")
ADMIN_ID = 6089008298  # ТВОЙ ID
YOUR_SITE_LINK = "https://t.me/rubup?startapp=a_qdraxk2" # ТВОЯ ССЫЛКА

users = {}
waiting_for_photo = set()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    
    if uid == ADMIN_ID:
        await update.message.reply_text("Вы админ. Ожидайте заявок.")
        return
    
    if uid not in users:
        users[uid] = "waiting_for_reg"
        kb = [[InlineKeyboardButton("📝 Регистрация", url=YOUR_SITE_LINK)]]
        await update.message.reply_text("❗Регистрация только для новых пользователей RubUp❗\n\nЕсли вы уже зарегистрированы, то бот не сможет выдавать сигналы.", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    if users[uid] == "waiting_for_reg":
        users[uid] = "pending"
        kb = [[InlineKeyboardButton("💳 Я пополнил", callback_data="paid_balance")]]
        await update.message.reply_text("Отлично! Теперь пополните баланс минимум на 500 рублей, после чего нажмите кнопку ниже:", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    if users[uid] == "pending":
        await update.message.reply_text("Ваша заявка на проверке. Ожидайте.")
        return
        
    if users[uid] == "waiting_for_photo":
        await update.message.reply_text("Пожалуйста, отправьте скриншот вашего профиля RubUp.")
        return
        
    if users[uid] == "waiting_for_admin":
        await update.message.reply_text("Ваша заявка отправлена администратору. Ожидайте.")
        return
        
    if users[uid] == "approved":
        kb = [[InlineKeyboardButton("🎲 Получить сигнал", callback_data="get_signal")]]
        await update.message.reply_text("Нажмите кнопку:", reply_markup=InlineKeyboardMarkup(kb))
        return
        
    if users[uid] == "rejected":
        await update.message.reply_text("Ваша заявка отклонена.")
        return

async def paid_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if uid not in users:
        return
    users[uid] = "waiting_for_photo"
    waiting_for_photo.add(uid)
    await query.edit_message_text("Вы зарегистрировались! Теперь отправьте скриншот вашего профиля RubUp (где видно баланс и имя):")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    if uid not in waiting_for_photo:
        return
    waiting_for_photo.remove(uid)
    users[uid] = "waiting_for_admin"
    
    if user.username:
        username_text = f"@{user.username}"
    else:
        username_text = "нету (скрыт)"
        
    admin_kb = [[InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{uid}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{uid}")]]
    caption_text = f"💰 Новая заявка на доступ!\nИмя: {user.full_name}\nЮзернейм: {username_text}\nID: {uid}\n\nПроверьте скриншот и одобрите доступ."
    
    await update.message.reply_text("✅ Спасибо! Ваша заявка отправлена администратору. Ожидайте.")
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=InlineKeyboardMarkup(admin_kb))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith(("approve_", "reject_")):
        return
    action, uid_str = data.split("_")
    uid = int(uid_str)
    if action == "approve":
        users[uid] = "approved"
        await query.edit_message_caption(caption="✅ Пользователь одобрен.")
        await context.bot.send_message(uid, "✅ Оплата подтверждена! Вы одобрены. Нажмите /start чтобы получить кнопку.")
        return
    users[uid] = "rejected"
    await query.edit_message_caption(caption="❌ Пользователь отклонён.")
    await context.bot.send_message(uid, "❌ Ваша заявка отклонена.")

async def signal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if uid not in users or users[uid] != "approved":
        await query.edit_message_text("Нет доступа.")
        return

    grid = ["🟦"] * 25
    diamond_positions = random.sample(range(25), 5)
    for pos in diamond_positions:
        grid[pos] = "💎"
        
    grid_text = ""
    for i in range(0, 25, 5):
        grid_text += " ".join(grid[i:i+5]) + "\n"
        
    await query.edit_message_text(f"🎲 Ваш сигнал:\n\n{grid_text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Еще раз", callback_data="get_signal")]]))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ Ведутся технические работы. Пожалуйста, попробуйте позже.")
    except Exception:
        pass

def main():
    # На Render прокси НЕ НУЖЕН
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(paid_balance_callback, pattern="^paid_balance$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve|reject)_"))
    app.add_handler(CallbackQueryHandler(signal_callback, pattern="^get_signal$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
