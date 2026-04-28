import json
import time
import urllib.request
import urllib.error
import boto3
import io
import logging
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from datetime import datetime
from boto3.dynamodb.conditions import Key
import os

BUCKET_NAME = os.environ["BUCKET_NAME"]  # Lambda env variable for bucket name

# Configuring logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Coins to track from CoinGecko
COINS = ["bitcoin", "ethereum", "solana"]
TABLE_NAME = os.environ.get("TABLE_NAME", "crypto-prices")
S3_KEY = "cryptowatch/latest.png" 

# Initializing AWS clients
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3")

def fetch_prices():
    """Fetching current USD price and market cap for all tracked coins from CoinGecko."""
    ids = ",".join(COINS)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_market_cap=true"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            # Logging prices to CloudWatch
            logger.info(f"Successfully fetched prices: { {c: data[c]['usd'] for c in COINS} }")
            return data
    except urllib.error.URLError as e:
        # Network failure
        logger.error(f"Network error fetching CoinGecko: {e}")
        raise
    except Exception as e:
        # Catch-all for unexpected issues
        logger.error(f"Unexpected error fetching prices: {e}")
        raise


def write_to_dynamo(data, ts):
    """Writing one timestamped record per coin to DynamoDB."""
    try:
        for coin in COINS:
            table.put_item(Item={
                "coin": coin,
                "timestamp": ts,   
                "price": str(data[coin]["usd"]),            
                "market_cap": str(data[coin]["usd_market_cap"]),
            })
        logger.info(f"Wrote {len(COINS)} records to DynamoDB at timestamp {ts}")
    except Exception as e:
        logger.error(f"Error writing to DynamoDB: {e}")
        raise


def generate_and_upload_plot():
    """Querying all data from DynamoDB, generating a price chart, and uploading it to S3."""
    try:
        # 3 stacked subplots, one per coin, each with its own y-axis scale
        fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
        plotted = 0  # How many coins were plotted
        colors = {"bitcoin": "#F7931A", "ethereum": "#627EEA", "solana": "#9945FF"}

        for i, coin in enumerate(COINS):
            ax = axes[i]

            # Querying all records for this coin
            resp = table.query(
                KeyConditionExpression=Key("coin").eq(coin),
                ScanIndexForward=True  # ascending by timestamp
            )
            items = resp["Items"]

            if not items:
                logger.warning(f"No data found for {coin}, skipping in plot")
                ax.set_visible(False)
                continue

            # Converting stored strings back to plottable types
            timestamps = [datetime.utcfromtimestamp(int(i["timestamp"])) for i in items]
            prices = [float(i["price"]) for i in items]
            ax.plot(timestamps, prices, label=coin.capitalize(), marker='o', markersize=3, color=colors[coin])
            ax.set_title(coin.capitalize())
            ax.set_ylabel("Price (USD)")
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
            ax.legend(loc="upper right")
            plotted += 1
            logger.info(f"Plotted {len(items)} points for {coin}")

        if plotted == 0:
            logger.warning("No data to plot, skipping S3 upload")
            plt.close()
            return

        axes[-1].set_xlabel("Time (UTC)")
        fig.suptitle("Crypto Prices Over Time", fontsize=14)
        fig.autofmt_xdate()
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)  
        plt.close()

        # Uploading to S3 at a fixed key so the URL is always the same
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=S3_KEY,
            Body=buf,
            ContentType="image/png",
        )
        logger.info(f"Plot uploaded to s3://{BUCKET_NAME}/{S3_KEY}")

    except Exception as e:
        logger.error(f"Error generating or uploading plot: {e}")
        raise


def lambda_handler(event, context):
    """Main entry point called by CloudWatch Events on schedule."""
    ts = int(time.time())
    logger.info(f"Invocation started at timestamp {ts}")
    try:
        data = fetch_prices()
        write_to_dynamo(data, ts)
        generate_and_upload_plot()
        logger.info("Invocation completed successfully")
    except Exception as e:
        logger.error(f"Invocation failed: {e}")
    return {"statusCode": 200}