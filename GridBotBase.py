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
        self._nonce = int(time.time() * 1000)  # Use timestamp in milliseconds

    def get_nonce(self):
        """Override the nonce to return a unique increasing number"""
        self._nonce += 1  # Increment nonce manually to avoid issues
        return self._nonce
    
    # Optionally, you can overwrite the `nonce()` method used in the sign function
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
invest_amount = fetch_investment_amount()

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
sell_prices = grid_prices[-5:]  # Top 5 prices for selling
buy_prices = grid_prices[:5]   # Bottom 5 prices for buying

# Kraken fee tiers based on volume (example values, update based on Kraken's docs)
kraken_fee_tiers = {
    "maker": 0.0016,  # 0.16% for makers
    "taker": 0.0026,  # 0.26% for takers
}

def calculate_fees(order_type, volume):
    """
    Calculate the trading fees based on Kraken's fee tiers.
    :param order_type: "maker" or "taker" (depends on order type).
    :return: The fee percentage.
    """
    maker_fee = kraken_fee_tiers["maker"]
    taker_fee = kraken_fee_tiers["taker"]
    return maker_fee if order_type == "maker" else taker_fee

def place_order(side, price, amount, fee_type='taker'):
    """Places a limit order."""
    try:
        order = exchange.create_limit_order(symbol, side, amount, price)
        print(f"{side.capitalize()} order placed: {amount} {symbol} at {price} with {fee_type} fee")
        return order
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

# Main Bot Logic with Fee Calculation
def run_grid_bot():
    # Track placed orders
    active_sell_orders = {}
    active_buy_orders = {}

    iteration_count = 0

    while True:
        iteration_count += 1
        print(f"Iteration {iteration_count} started")

        try:
            # Fetch the latest market price
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"Current price: {current_price}")

            # Loop through sell prices (top grid)
            for price in sell_prices:
                if price not in active_sell_orders and price < current_price:
                    # Only place sell orders above the current price
                    fee = calculate_fees("taker", volume=0)  # Use taker fees for selling
                    expected_profit = (current_price - price) * order_size
                    total_fee = expected_profit * fee
                    net_profit = expected_profit - total_fee

                    # Only place sell order if profit after fees is positive
                    if net_profit > 0:
                        order = place_order('sell', price, order_size, fee_type='taker')
                        if order:
                            active_sell_orders[price] = order
                    else:
                        print(f"Skipping sell order at {price} due to low net profit.")

            # Loop through buy prices (bottom grid)
            for price in buy_prices:
                if price not in active_buy_orders and price > current_price:
                    # Only place buy orders below the current price
                    fee = calculate_fees("maker", volume=0)  # Use maker fees for buying
                    expected_profit = (price - current_price) * order_size
                    total_fee = expected_profit * fee
                    net_profit = expected_profit - total_fee

                    # Only place buy order if profit after fees is positive
                    if net_profit > 0:
                        order = place_order('buy', price, order_size, fee_type='maker')
                        if order:
                            active_buy_orders[price] = order
                    else:
                        print(f"Skipping buy order at {price} due to low net profit.")

            # Check and cancel filled sell orders
            for price in list(active_sell_orders.keys()):
                order = active_sell_orders[price]
                try:
                    order_status = exchange.fetch_order(order['id'], symbol)
                    if order_status['status'] == 'closed':
                        print(f"Sell order filled at {price}")
                        del active_sell_orders[price]
                except Exception as e:
                    print(f"Error fetching sell order status: {e}")

            # Check and cancel filled buy orders
            for price in list(active_buy_orders.keys()):
                order = active_buy_orders[price]
                try:
                    order_status = exchange.fetch_order(order['id'], symbol)
                    if order_status['status'] == 'closed':
                        print(f"Buy order filled at {price}")
                        del active_buy_orders[price]
                except Exception as e:
                    print(f"Error fetching buy order status: {e}")

            # Wait before the next iteration
            print(f"Iteration {iteration_count} successfully completed --- >> ")
            time.sleep(60)

        except ccxt.base.errors.InvalidNonce as e:
            print(f"Nonce error: {e}. Skipping this iteration.")
            time.sleep(60)
            continue
        except Exception as e:
            print(f"Unexpected error: {e}. Skipping this iteration.")
            time.sleep(60)
            continue


# If this file is executed directly (not imported), run the bot
if __name__ == "__main__":
    run_grid_bot()
