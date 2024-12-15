from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests

# Your bot's token (replace with your actual token)
TELEGRAM_BOT_TOKEN = "8019171087:AAFM2tw_lzIBI-Qk_3bRIXiTb3x3MkX7NX0"

# Store user data for color and dibujo selections
user_colors = {}
user_dibujos = {}

# Base URL for your API
API_BASE_URL = "https://infopills.onrender.com/pills"

# Start command: fetches colors from API
async def start(update: Update, context: CallbackContext) -> None:
    try:
        # Fetch list of colors from API
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
            await update.message.reply_text("No pudimos listar los colroes.")
    except Exception as e:
        await update.message.reply_text(f"Error")

# Handle color selection
async def handle_color_selection(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.strip().lower()
    colores = context.user_data.get("colores")
    if colores and user_input in [chr(97 + i) for i in range(len(colores))]:  # Handle expected inputs ('a', 'b', ...)
        color_index = ord(user_input) - ord('a')  # Convert letter to index ('a' -> 0, 'b' -> 1, etc.)
        if 0 <= color_index < len(colores):
            selected_color = colores[color_index]
            # Fetch dibujos for selected color
            response = requests.get(f"{API_BASE_URL}/dibujos?color={selected_color}")
            if response.status_code == 200:
                dibujos = response.json()
                formatted_dibujos = "\n".join([f"{chr(97 + i)}. {dibujo}" for i, dibujo in enumerate(dibujos)])
                context.user_data["dibujos"] = dibujos
                context.user_data["selected_color"] = selected_color
                context.user_data["state"] = "waiting_for_dibujo"  # Change state to waiting for dibujo selection
                await update.message.reply_text(
                    f"Dibujos encontrados para el color {selected_color}:\n{formatted_dibujos}\n\nRespondé con una letra para seleccionar el dibujo(e.g., 'a' for dibujo)."
                )
            else:
                await update.message.reply_text("Hubo un error al buscar los dibujos.")
        else:
            await update.message.reply_text("Respuesta inválida. Por favor, elige un color válido ('a', 'b', etc.)")
    else:
        await update.message.reply_text("Respuesta inválida. Por favor, elige una letra válida de la lista.")

# Handle dibujo selection and retrieve /info
async def handle_dibujo_selection(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.strip().lower()
    dibujos = context.user_data.get("dibujos")
    selected_color = context.user_data.get("selected_color")
    if dibujos and user_input in ["a", "b", "c", "d", "e"]:
        dibujo_index = ord(user_input) - ord('a')  # Convert letter to index
        if 0 <= dibujo_index < len(dibujos):
            selected_dibujo = dibujos[dibujo_index]
            # Fetch info for the selected color and dibujo
            response = requests.get(f"{API_BASE_URL}/info?color={selected_color}&dibujo={selected_dibujo}")
            if response.status_code == 200:
                info = response.json()
                info_text = (
                    f"Info for {selected_dibujo} ({selected_color}):\n"
                    f"Información: {info['info']}\n"
                    f"Fecha: {info['date']}"
                )
                await update.message.reply_text(info_text)
                # Reset state after successful reply
                context.user_data["state"] = None
            else:
                await update.message.reply_text("Lo siento, no pude encontrar información.")
        else:
            await update.message.reply_text("Respuesta inválida. Por favor, elige un dibujo válido ('a', 'b', etc.)")
    else:
        await update.message.reply_text("Respuesta inválida. Por favor, elige una letra válida de la lista.")

# Unified message handler to check state and call appropriate function
async def message_handler(update: Update, context: CallbackContext) -> None:
    state = context.user_data.get("state")
    if state == "waiting_for_color":
        await handle_color_selection(update, context)
    elif state == "waiting_for_dibujo":
        await handle_dibujo_selection(update, context)
    else:
        await fallback(update, context)

# Fallback for any other input that doesn't match expectations
async def fallback(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Lo siento, no entendí tu mensaje. Por favor, usa el comando /start para comenzar."
    )

# Setup bot and start polling
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command to start bot and get color list
    application.add_handler(CommandHandler("start", start))

    # Unified message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Start polling to interact with the bot
    application.run_polling()

if __name__ == "__main__":
    main()