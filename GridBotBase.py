import os
from dotenv import load_dotenv
import ccxt
import time

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')

class CustomKraken(ccxt.kraken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nonce = int(time.time() * 1000)  # Use timestamp in milliseconds

    def nonce(self):
        """Override the nonce to return a unique increasing number"""
        self.nonce += 1  # Increment nonce manually to avoid issues
        return self.nonce
    
# Initialize Kraken exchange
exchange = CustomKraken({
    'apiKey': api_key,  
    'secret': secret_key,  
})

# Bot Parameters
symbol = 'ETH/EUR'  
lower_price = 1850  
upper_price = 4000  
grid_levels = 30  
invest_amout = 5000  

# Calculate grid step
grid_step = (upper_price - lower_price) / grid_levels

# Calculate order size
order_size = invest_amout / grid_levels

# Generate grid prices
grid_prices = [lower_price + i * grid_step for i in range(grid_levels + 1)]

# Fetch the trading fees
def get_trading_fees():
    """Fetches the current maker and taker fees for the exchange."""
    fee_info = exchange.fetch_trading_fee(symbol)
    maker_fee = fee_info['maker']
    taker_fee = fee_info['taker']
    return maker_fee, taker_fee

def place_order(side, price, amount, fee_type='taker'):
    """Places a limit order."""
    try:
        order = exchange.create_limit_order(symbol, side, amount, price)
        print(f"{side.capitalize()} order placed: {amount} {symbol} at {price} with {fee_type} fee")
        return order
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

# Main Bot Logic with Fee Decision
def run_grid_bot():
    # Track placed orders
    active_orders = {}

    # Fetch the current trading fees
    maker_fee, taker_fee = get_trading_fees()

    while True:
        # Fetch the latest market price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        print(f"Current price: {current_price}")

        # Check grid levels and place orders
        for price in grid_prices:
            if price not in active_orders:
                # Decide whether to place a buy or sell order based on the fees
                if price < current_price:
                    expected_profit = (current_price - price) * order_size
                    trading_fee = taker_fee if expected_profit > 0 else maker_fee
                    total_fee = expected_profit * trading_fee
                    net_profit = expected_profit - total_fee

                    # Only place sell order if the profit after fees is acceptable
                    if net_profit > 0:
                        order = place_order('sell', price, order_size, fee_type='taker')
                    else:
                        print(f"Skipping sell order at {price} due to high fees. Net profit after fees is negative.")
                elif price > current_price:
                    expected_profit = (price - current_price) * order_size
                    trading_fee = maker_fee if expected_profit > 0 else taker_fee
                    total_fee = expected_profit * trading_fee
                    net_profit = expected_profit - total_fee

                    # Only place buy order if the profit after fees is acceptable
                    if net_profit > 0:
                        order = place_order('buy', price, order_size, fee_type='maker')
                    else:
                        print(f"Skipping buy order at {price} due to high fees. Net profit after fees is negative.")

                if order:
                    active_orders[price] = order

        # Check and cancel filled orders
        for price in list(active_orders.keys()):
            order = active_orders[price]
            try:
                order_status = exchange.fetch_order(order['id'], symbol)
                if order_status['status'] == 'closed':
                    print(f"Order filled at {price}")
                    del active_orders[price]
            except Exception as e:
                print(f"Error fetching order status: {e}")

        time.sleep(10)  # Wait 10 seconds before the next check

# If this file is executed directly (not imported), run the bot
if __name__ == "__main__":
    run_grid_bot()
