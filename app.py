from flask import Flask
import threading
from GridBotBase import run_grid_bot  # Import the function from GridBotBase.py

# Initialize Flask app
app = Flask(__name__)

# Define a route that will be pinged
@app.route('/')
def home():
    return "Bot is running!"

# Function to run your grid bot in the background
def start_bot():
    print("Starting the bot...")
    run_grid_bot()

# Start the bot in a separate thread to run it in the background
def start_bot_thread():
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

# Run the Flask app
if __name__ == "__main__":
    start_bot_thread()  # Start the bot in the background
    app.run(debug=True, host='0.0.0.0', port=5000)
