from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend
from config import settings
# from .tasks import eth_price

TASKIQ_REDIS_URL = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"

result_backend = RedisAsyncResultBackend(
    redis_url=TASKIQ_REDIS_URL,
)

broker = (
    RedisStreamBroker(
        url=TASKIQ_REDIS_URL,
    )
    .with_result_backend(result_backend)
)

from taskiq_app.tasks import eth_price
