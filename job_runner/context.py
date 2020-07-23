import aioredis

from .config import Config


# quick and dirty
class Context:
    __slots__ = (
        "config",
        "redis",
    )

    def __init__(self, config: Config, redis: aioredis.ConnectionsPool):
        self.config = config
        self.redis = redis
