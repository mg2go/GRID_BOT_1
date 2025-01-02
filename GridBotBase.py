import os
from dotenv import load_dotenv
import ccxt
import time

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')

# Initialize Kraken exchange
exchange = ccxt.kraken({
    'apiKey': api_key,  # Replace with your Kraken API key
    'secret': secret_key,  # Replace with your Kraken API secret
})

# Bot Parameters
symbol = 'ETH/EUR'  # Trading pair
lower_price = 1850  # Lower limit of the grid
upper_price = 4000  # Upper limit of the grid
grid_levels = 30  # Number of grid levels
invest_amout = 5000  # Total amount to be invested in EUR

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
    maker_fee = fee_info['maker']  # Maker fee (if you're adding liquidity)
    taker_fee = fee_info['taker']  # Taker fee (if you're taking liquidity)
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
                    # Check if placing a sell order is profitable after fees
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
                    # Check if placing a buy order is profitable after fees
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

# Start the bot
run_grid_bot()