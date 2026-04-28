# ds5220-dp3

## Data source
I tracked the CoinGecko API every 15 minutes to determine how three of the top cryptocurrencies (Bitcoin, Ethereum, and Solana) change in price. I thought it would be extremely interesting to see how volatile each crypto would be, considering that crypto prices change constantly. With such a small time window, I wanted to see if there were any large increases or decreases in price, which there were. 

## Sampling and storage schema
Prices are sampled every 15 minutes via a CloudWatch EventBridge timer that 
triggers an AWS Lambda function.

Data is stored in a DynamoDB table (`crypto-prices`) with the following schema:

| Field | Type | Description |
|---|---|---|
| `coin` | String (Partition Key) | Coin ID (bitcoin, ethereum, solana) |
| `timestamp` | Number (Sort Key) | Unix timestamp of the sample |
| `price` | String | Price in USD at time of sample |
| `market_cap` | String | Market cap in USD at time of sample |

## API Resources

**`GET /`**: Returns the "about" section that details the project descriptions and lists the available resources

**`GET /current`**: Returns the most recent price from each coin

**`GET /trend`**: Returns the highest price, lowest price, average price, and whether the trend direction is up or down for each coin within the entire collection window

**`GET /plot`**: Returns the URL of the plot of each coin's prices, which is stored in S3.

## Stretch Goals
No stretch goals were implemented for this project.






