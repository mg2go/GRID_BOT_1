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
        self._nonce = int(time.time() * 1000)

    def get_nonce(self):
        self._nonce += 1
        return self._nonce
    
    def nonce(self):
        return self.get_nonce()

exchange = CustomKraken({
    'apiKey': api_key,
    'secret': secret_key,
})

symbol = 'ETH/EUR'
lower_price = 1850
upper_price = 4000
grid_levels = 10

def get_available_balance(currency):
    try:
        balance = exchange.fetch_balance()
        return balance['free'].get(currency, 0)
    except Exception as e:
        print(f"Error fetching balance for {currency}: {e}")
        return 0

def fetch_investment_amount():
    try:
        return float(os.environ.get('INVEST_AMOUNT', '0.0'))
    except ValueError:
        print("Error parsing INVEST_AMOUNT. Resetting to 0.0.")
        os.environ['INVEST_AMOUNT'] = '0.0'
        return 0.0

invest_amount = fetch_investment_amount()
grid_step = (upper_price - lower_price) / grid_levels

def calculate_order_size(current_price):
    eth_balance = get_available_balance('ETH')
    eur_balance = get_available_balance('EUR')
    order_size_eth = eth_balance / grid_levels
    order_size_eur = (eur_balance / grid_levels) / current_price
    return min(order_size_eth, order_size_eur)

def calculate_fees(order_type, volume):
    kraken_fee_tiers = {
        "maker": 0.0016,
        "taker": 0.0026,
    }
    maker_fee = kraken_fee_tiers["maker"]
    taker_fee = kraken_fee_tiers["taker"]
    return maker_fee if order_type == "maker" else taker_fee

def get_total_invested():
    try:
        return float(os.environ.get('TOTAL_INVESTED', '0.0'))
    except ValueError:
        print("Error parsing TOTAL_INVESTED. Resetting to 0.0.")
        os.environ['TOTAL_INVESTED'] = '0.0'
        return 0.0

def update_total_invested(amount):
    total_invested = get_total_invested() + amount
    os.environ['TOTAL_INVESTED'] = str(total_invested)

def place_order(side, price, amount, fee_type='taker'):
    try:
        order = exchange.create_limit_order(symbol, side, amount, price)
        print(f"{side.capitalize()} order placed: {amount} {symbol} at {price}")
        update_total_invested(amount * price if side == 'buy' else -amount * price)
        return order
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

def run_grid_bot():
    grid_prices = [lower_price + i * grid_step for i in range(grid_levels + 1)]
    sell_prices = grid_prices[-5:]
    buy_prices = grid_prices[:5]
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

            order_size = calculate_order_size(current_price)

            for price in sell_prices[:]:
                if price not in active_sell_orders and price < current_price:
                    fee = calculate_fees("taker", volume=0)
                    eth_balance = get_available_balance('ETH')
                    if eth_balance >= order_size:
                        order = place_order('sell', price, order_size, fee_type='taker')
                        if order:
                            active_sell_orders[price] = order
                            sell_prices.remove(price)
                    else:
                        print(f"Insufficient ETH balance to place sell order. Available: {eth_balance}, Required: {order_size}")

            for price in buy_prices[:]:
                total_invested = get_total_invested()
                potential_investment = order_size * price

                if total_invested + potential_investment > invest_amount:
                    print(f"Skipping buy order at {price}. Total investment would exceed {invest_amount}.")
                    continue

                if price not in active_buy_orders and price > current_price:
                    fee = calculate_fees("maker", volume=0)
                    eur_balance = get_available_balance('EUR')
                    if eur_balance >= potential_investment:
                        order = place_order('buy', price, order_size, fee_type='maker')
                        if order:
                            active_buy_orders[price] = order
                            buy_prices.remove(price)
                    else:
                        print(f"Insufficient EUR balance to place buy order. Available: {eur_balance}, Required: {potential_investment}")

            time.sleep(60)

        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_grid_bot()