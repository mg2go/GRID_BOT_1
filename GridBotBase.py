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
grid_levels = 30  
invest_amout = 5000  

# Calculate grid step
grid_step = (upper_price - lower_price) / grid_levels

# Calculate order size
order_size = invest_amout / grid_levels

# Generate grid prices
grid_prices = [lower_price + i * grid_step for i in range(grid_levels + 1)]

# Kraken fee tiers based on volume (example values, update based on Kraken's docs)
kraken_fee_tiers = {
    "maker": 0.0016,  # 0.16% for makers
    "taker": 0.0026,  # 0.26% for takers
}

def calculate_fees(order_type, volume):
    """
    Calculate the trading fees based on Kraken's fee tiers.
    :param order_type: "maker" or "taker" (depends on order type).
    :param volume: The total volume traded in the last 30 days (used to determine fee tier).
    :return: The fee percentage.
    """
    # Default to basic fee tiers for now
    maker_fee = kraken_fee_tiers["maker"]
    taker_fee = kraken_fee_tiers["taker"]

    # Logic to adjust fees based on trading volume can go here if needed
    if order_type == "maker":
        return maker_fee
    elif order_type == "taker":
        return taker_fee
    else:
        raise ValueError(f"Invalid order type: {order_type}")


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
    active_orders = {}
    i = 0;
    while True:
        i=i+1
        print("Number of iterations is "+ i)
        try:
            # Fetch the latest market price
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"Current price: {current_price}")

            # Check grid levels and place orders
            for price in grid_prices:
                if price not in active_orders:
                    # Decide whether to place a buy or sell order
                    if price < current_price:
                        # Use taker fee for immediate execution
                        fee = calculate_fees("taker", volume=0)  # Update "volume" based on actual data if needed
                        expected_profit = (current_price - price) * order_size
                        total_fee = expected_profit * fee
                        net_profit = expected_profit - total_fee

                        # Only place sell order if the profit after fees is acceptable
                        if net_profit > 0:
                            order = place_order('sell', price, order_size, fee_type='taker')
                        else:
                            print(f"Skipping sell order at {price} due to high fees. Net profit after fees is negative.")
                    elif price > current_price:
                        # Use maker fee for limit orders
                        fee = calculate_fees("maker", volume=0)  # Update "volume" based on actual data if needed
                        expected_profit = (price - current_price) * order_size
                        total_fee = expected_profit * fee
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

            # Wait 60 seconds before the next check
            print("Iteration ended successfully ---- >> ")
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
