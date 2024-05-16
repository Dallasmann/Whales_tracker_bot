import os 
from dotenv import load_dotenv
import telegram
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from etherscan import Etherscan
from time import sleep

# Load environment variables from .env file
load_dotenv()

# import API from Render environment
telegram_key = os.getenv("TELEGRAM_TOKEN")
etherscan_key= os.getenv("ETHERSCAN_API_KEY")

etherscan = Etherscan(etherscan_key)

# Conversation states
CHOOSING_ACTION, RECEIVING_NICKNAME, RECEIVING_ADDRESS, RECEIVING_DELETE_NAME = range(4)

# Function to start monitoring transactions
def monitor_transactions(update, context):
    addresses = context.user_data.get('addresses')
    if not addresses:
        update.message.reply_text("You haven't added any addresses yet.")
        return ConversationHandler.END
    
    update.message.reply_text("Monitoring transactions for the following addresses:")
    for address, nickname in addresses.items():
        update.message.reply_text(f"Nickname: {nickname}\nAddress: {address}")
    
    while True:
        for address in addresses:
            # Get recent transactions for each specified address
            transactions = etherscan.get_transactions_by_address(address)
            if transactions['status'] == '1' and len(transactions['result']) > 0:
                for tx in transactions['result']:
                    message = f"New transaction detected for address {address} (Nickname: {addresses[address]}):\n"
                    message += f"Transaction Hash: {tx['hash']}\n"
                    message += f"Amount: {tx['value']} Wei\n"
                    message += f"Block: {tx['blockNumber']}\n"
                    message += f"Timestamp: {tx['timeStamp']}\n"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=get_buttons_markup())
        sleep(60)

# Function to get inline keyboard buttons markup with icons
def get_buttons_markup():
    # Define icons for each button
    icon_check = "✅"
    icon_add = "➕"
    icon_delete = "❌"

    # Create buttons with icons
    buttons = [
        InlineKeyboardButton(f"{icon_check} List", callback_data='check_addresses'),
        InlineKeyboardButton(f"{icon_add} Add", callback_data='add_address'),
        InlineKeyboardButton(f"{icon_delete} Delete", callback_data='delete_address')
    ]

    # Arrange buttons horizontally
    keyboard = [buttons]

    # Create InlineKeyboardMarkup with the arranged buttons
    return InlineKeyboardMarkup(keyboard)

# Function to start the conversation and display welcome message
def start(update, context):
    # Get user's ID
    user_id = update.message.from_user.id
    
    # Check if the user has already interacted with the bot before
    if 'addresses' not in context.user_data:
        # First time user, display welcome message and instructions
        welcome_message = (
            "Welcome to the Whales tracker bot! 🐋\n\n"
            "Enter the Ethereum address you would like to follow using the buttons below. "
            "You will receive a notification whenever the address makes a transaction. 😉"
        )
        update.message.reply_text(welcome_message, reply_markup=get_buttons_markup())
    else:
        # Returning user, display standard message
        update.message.reply_text('What would you like to do?', reply_markup=get_buttons_markup())
    
    # Set user's state to CHOOSING_ACTION
    return CHOOSING_ACTION

# Function to handle button clicks
def button_click(update, context):
    query = update.callback_query
    query.answer()
    if query.data == 'check_addresses':
        addresses = context.user_data.get('addresses')
        if not addresses:
            query.edit_message_text(text="You haven't added any addresses yet.", reply_markup=get_buttons_markup())
        else:
            message = "Addresses you are currently monitoring:\n"
            for address, nickname in addresses.items():
                message += f"Nickname: {nickname}\nAddress: {address}\n\n"
            query.edit_message_text(text=message, reply_markup=get_buttons_markup())
    elif query.data == 'add_address':
        query.edit_message_text(text="Please enter the nickname for this address:")
        return RECEIVING_NICKNAME
    elif query.data == 'delete_address':
        query.edit_message_text(text="Please enter the nickname of the address you want to delete:")
        return RECEIVING_DELETE_NAME

# Function to receive the nickname for a new address
def receive_nickname(update, context):
    context.user_data['temp_nickname'] = update.message.text
    update.message.reply_text("Please enter the Ethereum address:")
    return RECEIVING_ADDRESS

# Function to receive the new address
def receive_address(update, context):
    nickname = context.user_data['temp_nickname']
    address = update.message.text
    if len(address) != 42 or not address.startswith('0x'):
        update.message.reply_text("The Ethereum address entered is not valid. Please try again.")
        return RECEIVING_ADDRESS
    else:
        addresses = context.user_data.setdefault('addresses', {})
        addresses[address] = nickname
        update.message.reply_text(f"The nickname '{nickname}' has been added for the Ethereum address '{address}'.", reply_markup=get_buttons_markup())
        return ConversationHandler.END

# Function to cancel the conversation
def cancel(update, context):
    update.message.reply_text("Conversation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Main function
def main():
    # Create an Updater instance with your bot token
    updater = Updater(token=telegram_key, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Create a conversation handler to handle user interactions
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [CallbackQueryHandler(button_click)],
            RECEIVING_NICKNAME: [MessageHandler(Filters.text & ~Filters.command, receive_nickname)],
            RECEIVING_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, receive_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add the conversation handler to the dispatcher
    dp.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

# Execute the main function if the script is run directly
if __name__ == '__main__':
    main()
