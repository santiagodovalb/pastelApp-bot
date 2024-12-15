import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os

# Your bot's token (replace with your actual token)
TELEGRAM_BOT_TOKEN = "8019171087:AAFM2tw_lzIBI-Qk_3bRIXiTb3x3MkX7NX0"

# Store user data for color and dibujo selections
user_colors = {}
user_dibujos = {}

# Base URL for your API
API_BASE_URL = "https://infopills.onrender.com/pills"

# FastAPI app initialization
app = FastAPI()

# Telegram bot application (without `.initialize()`)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.initialize()

# Handlers
start_handler = CommandHandler("start", lambda update, context: start(update, context))
message_handler_instance = MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: unified_message_handler(update, context))

# FastAPI startup event for initialization
@app.on_event("startup")
async def on_startup():
    print("Starting Telegram bot...")
    # Initialize Telegram Application
    
    # Add handlers
    application.add_handler(start_handler)
    application.add_handler(message_handler_instance)

    # Set webhook
    webhook_url = "https://pastelapp-bot.vercel.app/webhook"  # Replace with your public webhook URL
    await application.bot.set_webhook(webhook_url)
    print(f"Webhook set: {webhook_url}")
    print("Telegram bot initialized.")

# Shutdown event
@app.on_event("shutdown")
async def on_shutdown():
    print("Shutting down Telegram bot...")
    await application.shutdown()

# Start command: fetches colors from API
async def start(update: Update, context: CallbackContext) -> None:
    try:
        response = requests.get(f"{API_BASE_URL}/colores")
        if response.status_code == 200:
            colores = response.json()
            context.user_data["colores"] = colores
            context.user_data["state"] = "waiting_for_color"  # Set state to waiting for color selection
            formatted_list = "\n".join([f"{chr(97 + i)}. {color}" for i, color in enumerate(colores)])
            await update.message.reply_text(
                f"Colores:\n{formatted_list}\n\nRespondé con una letra para seleccionar el color (e.g., 'a' for verde)."
            )
        else:
            await update.message.reply_text("No pudimos listar los colores.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Unified message handler
async def unified_message_handler(update: Update, context: CallbackContext) -> None:
    state = context.user_data.get("state")
    if state == "waiting_for_color":
        await handle_color_selection(update, context)
    elif state == "waiting_for_dibujo":
        await handle_dibujo_selection(update, context)
    else:
        await fallback(update, context)

# Fallback for unexpected messages
async def fallback(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Lo siento, no entendí tu mensaje. Por favor, usa el comando /start para comenzar."
    )

# Telegram webhook route
@app.post("/webhook")
async def webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error in processing update: {e}")
        raise HTTPException(status_code=422, detail=str(e))

# FastAPI runner
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)