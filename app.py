import logging
import boto3
from chalice import Chalice
from boto3.dynamodb.conditions import Key

# Initializing Chalice app
app = Chalice(app_name='cryptowatch')

# Configuring logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
COINS = ["bitcoin", "ethereum", "solana"]
TABLE_NAME = "crypto-prices"
PLOT_URL = "https://cryptowatch-dp3-xtm9px.s3.amazonaws.com/cryptowatch/latest.png"

# Initializing DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table(TABLE_NAME)


def get_latest_price(coin):
    """Querying DynamoDB for the most recent record for a given coin."""
    try:
        resp = table.query(
            KeyConditionExpression=Key("coin").eq(coin),
            ScanIndexForward=False, 
            Limit=1
        )
        items = resp.get("Items", [])
        if not items:
            logger.warning(f"No items found for {coin}")
            return None
        logger.info(f"Fetched latest price for {coin}: {items[0]['price']}")
        return items[0]
    except Exception as e:
        logger.error(f"Error querying latest price for {coin}: {e}")
        return None


def get_all_prices(coin):
    """Querying DynamoDB for all records for a given coin."""
    try:
        resp = table.query(
            KeyConditionExpression=Key("coin").eq(coin),
            ScanIndexForward=True  
        )
        items = resp.get("Items", [])
        logger.info(f"Fetched {len(items)} records for {coin}")
        return items
    except Exception as e:
        logger.error(f"Error querying all prices for {coin}: {e}")
        return []


@app.route('/')
def index():
    """Describes the project and lists available resources."""
    logger.info("GET / called")
    return {
        "about": "This project tracks the prices of Bitcoin, Ethereum, and Solana every 15 minutes using the CoinGecko API, building a time series to reveal trends and volatility over time.",
        "resources": ["current", "trend", "plot"]
    }


@app.route('/current')
def current():
    """Returns the most recent price for each tracked coin."""
    logger.info("GET /current called")
    try:
        parts = []
        for coin in COINS:
            item = get_latest_price(coin)
            if item:
                price = float(item["price"])
                parts.append(f"{coin.capitalize()}: ${price:,.2f}")
            else:
                logger.warning(f"No data available for {coin}")
                parts.append(f"{coin.capitalize()}: N/A")
        response = " | ".join(parts)
        logger.info(f"Returning current prices: {response}")
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in /current: {e}")
        return {"response": "Error fetching current prices."}


@app.route('/trend')
def trend():
    """Returns high, low, average, and direction for each coin over the collection window."""
    logger.info("GET /trend called")
    try:
        parts = []
        for coin in COINS:
            items = get_all_prices(coin)
            if not items:
                logger.warning(f"No trend data for {coin}")
                parts.append(f"{coin.capitalize()}: N/A")
                continue
            prices = [float(i["price"]) for i in items]
            high = max(prices)
            low = min(prices)
            avg = sum(prices) / len(prices)
            direction = "up" if prices[-1] > prices[0] else "down"
            parts.append(f"{coin.capitalize()}: High ${high:,.2f} | Low ${low:,.2f} | Avg ${avg:,.2f} {direction}")
            logger.info(f"{coin} trend - high: {high}, low: {low}, avg: {avg:.2f}, direction: {direction}")
        return {"response" : " || ".join(parts)}
    except Exception as e:
        logger.error(f"Error in /trend: {e}")
        return {"response": "Error fetching trend data."}


@app.route('/plot')
def plot():
    """Returns the S3 URL of the latest price chart."""
    logger.info("GET /plot called")
    return {"response": PLOT_URL}
