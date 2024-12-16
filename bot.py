from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests
import logging

# Your bot's token
TELEGRAM_BOT_TOKEN = "8019171087:AAFM2tw_lzIBI-Qk_3bRIXiTb3x3MkX7NX0"
API_BASE_URL = "https://infopills.onrender.com/pills"

# Initialize FastAPI
app = FastAPI()

# Create Telegram Bot and Application
bot = Bot(TELEGRAM_BOT_TOKEN)
if "application" not in globals():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers only once
if len(application.handlers) == 0:
    # Store user states
    async def start(update: Update, context: CallbackContext) -> None:
        try:
            response = requests.get(f"{API_BASE_URL}/colores")
            if response.status_code == 200:
                colores = response.json()
                context.user_data["colores"] = colores
                context.user_data["state"] = "waiting_for_color"
                formatted_list = "\n".join(
                    [f"{chr(97 + i)}. {color}" for i, color in enumerate(colores)]
                )
                await update.message.reply_text(
                    f"Colores disponibles:\n{formatted_list}\n"
                    "Respondé con una letra para seleccionar un color (por ejemplo, 'a')."
                )
            else:
                await update.message.reply_text("Error al obtener la lista de colores.")
        except Exception as e:
            await update.message.reply_text(f"Hubo un error: {e}")

    async def handle_color_selection(update: Update, context: CallbackContext) -> None:
        user_input = update.message.text.strip().lower()
        colores = context.user_data.get("colores")
        if colores and user_input in [chr(97 + i) for i in range(len(colores))]:
            color_index = ord(user_input) - ord('a')
            selected_color = colores[color_index]
            context.user_data["selected_color"] = selected_color

            response = requests.get(f"{API_BASE_URL}/dibujos?color={selected_color}")
            if response.status_code == 200:
                dibujos = response.json()
                context.user_data["dibujos"] = dibujos
                context.user_data["state"] = "waiting_for_dibujo"
                formatted_dibujos = "\n".join(
                    [f"{chr(97 + i)}. {dibujo}" for i, dibujo in enumerate(dibujos)]
                )
                await update.message.reply_text(
                    f"Dibujos para {selected_color}:\n{formatted_dibujos}\n"
                    "Seleccioná un dibujo respondiendo con una letra (ej. 'a')."
                )
            else:
                await update.message.reply_text(
                    "Error al obtener los dibujos para el color seleccionado."
                )
        else:
            await update.message.reply_text(
                "Selección inválida. Por favor selecciona un color válido."
            )

    async def handle_dibujo_selection(update: Update, context: CallbackContext) -> None:
        user_input = update.message.text.strip().lower()
        dibujos = context.user_data.get("dibujos")
        selected_color = context.user_data.get("selected_color")
        if dibujos and user_input in [chr(97 + i) for i in range(len(dibujos))]:
            dibujo_index = ord(user_input) - ord('a')
            selected_dibujo = dibujos[dibujo_index]
            response = requests.get(
                f"{API_BASE_URL}/info?color={selected_color}&dibujo={selected_dibujo}"
            )
            if response.status_code == 200:
                info = response.json()
                await update.message.reply_text(
                    f"Información sobre {selected_dibujo} ({selected_color}):\n"
                    f"Detalles: {info['info']}\nFecha: {info['date']}"
                )
                context.user_data["state"] = None
            else:
                await update.message.reply_text("Error al obtener la información.")
        else:
            await update.message.reply_text(
                "Selección inválida. Por favor selecciona un dibujo válido."
            )

    async def message_handler(update: Update, context: CallbackContext) -> None:
        state = context.user_data.get("state")
        if state == "waiting_for_color":
            await handle_color_selection(update, context)
        elif state == "waiting_for_dibujo":
            await handle_dibujo_selection(update, context)
        else:
            await update.message.reply_text(
                "Lo siento, no entendí. Usa /start para comenzar."
            )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Set webhook dynamically
@app.on_event("startup")
async def on_startup():
    webhook_url = "https://pastelapp-bot.vercel.app/webhook"  # Update your Vercel domain
    try:
        await application.start()  # Start the Telegram application
        await bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")

# FastAPI endpoint to receive webhook updates
@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"Webhook received: {payload}")
        update = Update.de_json(payload, bot)
        logging.info(f"Processing update: {update}")
        await application.update_queue.put(update)
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
