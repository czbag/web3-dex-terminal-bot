import aiohttp
from taskiq_app.broker import broker
from redis.asyncio import Redis
from config import settings

ETH_KEY = "eth:usd"
REDIS_DATA_URL = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"


async def fetch_price():
    async with aiohttp.ClientSession() as client:
        async with client.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        ) as resp:
            data = await resp.json()
            return data["price"]


@broker.task(schedule=[{"cron": "* * * * *"}])
async def update_eth_price_task():
    redis = Redis.from_url(REDIS_DATA_URL, decode_responses=True)
    price = await fetch_price()
    await redis.set(ETH_KEY, price, ex=600)
    await redis.aclose()
