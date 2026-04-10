import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

# Ваш токен бота
TOKEN = '8763345099:AAEVX24IbUnS2PxVdm28H3BayL7WIRcFZdA'
# Ваш Telegram user_id (админ)
ADMIN_ID = 7993751174  # Замените на свой user_id

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

waiting_users = set()
active_chats = {}
# user_id текущего активного чата для админа
current_chat = None
# Множество всех пользователей, которые когда-либо писали админу
chat_history = set()
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = []
    # Активные заявки
    if waiting_users:
        for uid in waiting_users:
            user = await context.bot.get_chat(uid)
            username = user.username if user.username else "нет ника"
            keyboard.append([
                InlineKeyboardButton(f"@{username} (ID: {uid})", callback_data=f"select_{uid}")
            ])
    # История чатов
    if chat_history:
        keyboard.append([InlineKeyboardButton("--- История чатов ---", callback_data="none")])
        for uid in chat_history:
            if uid not in waiting_users:
                user = await context.bot.get_chat(uid)
                username = user.username if user.username else "нет ника"
                keyboard.append([
                    InlineKeyboardButton(f"@{username} (ID: {uid})", callback_data=f"history_{uid}")
                ])
    # Кнопка отмены чата для админа
    if current_chat:
        keyboard.append([InlineKeyboardButton("❌ Завершить чат", callback_data="end_chat")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Заявки и история чатов:", reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_chat
    if update.effective_user.id != ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("select_"):
        user_id = int(data.split('_')[1])
        current_chat = user_id
        waiting_users.discard(user_id)
        active_chats[user_id] = True
        chat_history.add(user_id)
        await query.edit_message_text(f"Чат с пользователем {user_id} активирован. Теперь вы можете писать ему.")
        await context.bot.send_message(
            chat_id=user_id,
            text="Админ принял ваш запрос. Теперь вы можете общаться. Напишите сообщение."
        )
    elif data.startswith("history_"):
        user_id = int(data.split('_')[1])
        current_chat = user_id
        active_chats[user_id] = True
        chat_history.add(user_id)
        await query.edit_message_text(f"Чат с пользователем {user_id} из истории активирован. Теперь вы можете писать ему.")
        await context.bot.send_message(
            chat_id=user_id,
            text="Админ снова открыл чат с вами. Можете продолжить общение."
        )
    elif data == "end_chat":
        if current_chat:
            await context.bot.send_message(
                chat_id=current_chat,
                text="Чат с админом завершён."
            )
            active_chats.pop(current_chat, None)
            await query.edit_message_text("Чат завершён.")
            current_chat = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [["Связаться с админом"]]
    # Кнопка "Админ-панель" всегда для админа
    if user_id == ADMIN_ID:
        keyboard.append(["Админ-панель"])
    # Кнопка отмены заявки для пользователя
    if user_id in waiting_users:
        keyboard.append(["Отменить заявку"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать! Нажмите кнопку ниже, чтобы связаться с админом.",
        reply_markup=reply_markup
    )

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id in waiting_users or active_chats.get(user_id):
        await update.message.reply_text("Вы уже отправили запрос или общаетесь с админом.")
        return
    waiting_users.add(user_id)
    chat_history.add(user_id)
    keyboard = [["Отменить заявку"]]
    await update.message.reply_text("Запрос отправлен. Ожидайте ответа администратора.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    # Уведомление админу с ником и ID
    username = user.username if user.username else "нет ника"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Новый запрос на общение!\nНик: @{username}\nUser ID: {user_id}"
    )

async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("Ваша заявка отменена.", reply_markup=ReplyKeyboardMarkup([["Связаться с админом"]], resize_keyboard=True))
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {user_id} отменил заявку.")
    else:
        await update.message.reply_text("У вас нет активной заявки.")



async def relay_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_chat
    user_id = update.effective_user.id
    # Сообщение от пользователя админу
    if user_id in active_chats and active_chats[user_id]:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Сообщение от пользователя {user_id}:\n{update.message.text}"
        )
    # Сообщение от админа пользователю (если выбран чат)
    elif user_id == ADMIN_ID:
        if current_chat:
            if update.message.text == "/end":
                await context.bot.send_message(
                    chat_id=current_chat,
                    text="Чат с админом завершён."
                )
                active_chats.pop(current_chat, None)
                await update.message.reply_text("Чат завершён.")
                current_chat = None
            else:
                await context.bot.send_message(
                    chat_id=current_chat,
                    text=f"Админ: {update.message.text}"
                )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex("Админ-панель"), admin_panel))
    app.add_handler(MessageHandler(filters.Regex("Связаться с админом"), contact_admin))
    app.add_handler(MessageHandler(filters.Regex("Отменить заявку"), cancel_request))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/end$"), relay_message))
    app.add_handler(MessageHandler(filters.ALL, relay_message))
    app.add_handler(CallbackQueryHandler(admin_callback))
    print('Анонимный бот запущен. Для остановки нажмите Ctrl+C.')
    app.run_polling()
