import os
from dotenv import load_dotenv
import ccxt
import time

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')

# Initialize the total invested tracker
if 'TOTAL_INVESTED' not in os.environ:
    os.environ['TOTAL_INVESTED'] = '0.0'  # Initialize if not present

class CustomKraken(ccxt.kraken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._nonce = int(time.time() * 1000)  # Use timestamp in milliseconds

    def get_nonce(self):
        """Override the nonce to return a unique increasing number"""
        self._nonce += 1  # Increment nonce manually to avoid issues
        return self._nonce
    
    def nonce(self):
        return self.get_nonce()

# Initialize Kraken exchange
exchange = CustomKraken({
    'apiKey': api_key,
    'secret': secret_key,
})

# Bot Parameters
symbol = 'ETH/EUR'
lower_price = 1850
upper_price = 4000
grid_levels = 10

def get_available_balance(currency):
    """Fetch available balance for a specific currency."""
    try:
        balance = exchange.fetch_balance()
        return balance['free'].get(currency, 0)
    except Exception as e:
        print(f"Error fetching balance for {currency}: {e}")
        return 0
    
# Fetch available balance dynamically
def fetch_investment_amount():
    try:
        balance = exchange.fetch_balance()
        quote_currency = 'EUR'  # For ETH/EUR, 'EUR' is the quote currency
        available_balance = balance['free'][quote_currency]
        print(f"Available {quote_currency} balance: {available_balance}")
        return available_balance
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return 0  # Fallback to 0 if balance fetch fails

# Fetch the investment amount dynamically from the balance
invest_amount = 2000 #invest only 2000 for now
#fetch_investment_amount()

# Calculate grid step
grid_step = (upper_price - lower_price) / grid_levels

# Fetch the latest ticker for current price
ticker = exchange.fetch_ticker(symbol)
current_price = ticker['last']

# Calculate order size
order_size = (invest_amount / grid_levels) / current_price

# Generate grid prices
grid_prices = [lower_price + i * grid_step for i in range(grid_levels + 1)]

# Split grid prices into sell and buy grids
sell_prices = grid_prices[-5:]
buy_prices = grid_prices[:5]

# Kraken fee tiers based on volume
kraken_fee_tiers = {
    "maker": 0.0016,
    "taker": 0.0026,
}

def calculate_fees(order_type, volume):
    maker_fee = kraken_fee_tiers["maker"]
    taker_fee = kraken_fee_tiers["taker"]
    return maker_fee if order_type == "maker" else taker_fee

def get_total_invested():
    """Retrieve the current total invested value from the environment."""
    try:
        return float(os.environ.get('TOTAL_INVESTED', '0.0'))
    except ValueError:
        print("Error parsing TOTAL_INVESTED. Resetting to 0.0.")
        os.environ['TOTAL_INVESTED'] = '0.0'
        return 0.0

def update_total_invested(amount):
    """Update the TOTAL_INVESTED environmental variable."""
    try:
        current_invested = get_total_invested()
        os.environ['TOTAL_INVESTED'] = str(current_invested + amount)
        print(f"Updated total invested: {os.environ['TOTAL_INVESTED']}")
    except Exception as e:
        print(f"Error updating total invested: {e}")

def place_order(side, price, amount, fee_type='taker'):
    """Places a limit order and updates the total invested."""
    try:
        order = exchange.create_limit_order(symbol, side, amount, price)
        print(f"{side.capitalize()} order placed: {amount} {symbol} at {price} with {fee_type} fee")

        # Update total invested
        if side == 'buy':
            update_total_invested(amount * price)  # Add to total invested
        elif side == 'sell':
            update_total_invested(-(amount * price))  # Subtract from total invested

        return order
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

# Main Bot Logic with Fee Calculation
def run_grid_bot():
    active_sell_orders = {}
    active_buy_orders = {}
    iteration_count = 0

    while True:
        iteration_count += 1
        print(f"Iteration {iteration_count} started")

        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"Current price: {current_price}")

            # Sell orders
            for price in sell_prices[:]:
                if price not in active_sell_orders and price < current_price:
                    fee = calculate_fees("taker", volume=0)
                    eth_balance = get_available_balance('ETH')  # Replace 'ETH' with the base currency
                    if eth_balance >= order_size:
                        order = place_order('sell', price, order_size, fee_type='taker')
                        if order:
                            active_sell_orders[price] = order
                            sell_prices.remove(price)
                    else:
                        print(f"Insufficient ETH balance to place sell order. Available: {eth_balance}, Required: {order_size}")
            # Buy orders
            for price in buy_prices[:]:
                total_invested = get_total_invested()
                potential_investment = order_size * price

                # Check if the total investment exceeds the allowed limit
                if total_invested + potential_investment > invest_amount:
                    print(f"Skipping buy order at {price}. Total investment would exceed {invest_amount}.")
                    continue

                if price not in active_buy_orders and price > current_price:
                    fee = calculate_fees("maker", volume=0)
                    order = place_order('buy', price, order_size, fee_type='maker')
                    if order:
                        active_buy_orders[price] = order
                        buy_prices.remove(price)

            # Handle completed orders (similar to earlier logic)

            time.sleep(60)

        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_grid_bot()
