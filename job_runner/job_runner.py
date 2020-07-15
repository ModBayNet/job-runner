# ModBay generic job runner.
# Copyright (C) 2020  Eugene Ershov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import copy
import logging

import aioredis

from arpq import MessageQueue

from .job import Job, UnknownJobError, MalformedPayloadError
from .config import Config

log = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, config: Config):
        self._config = config

    async def _get_redis(self) -> aioredis.ConnectionsPool:
        log.debug("connecting to redis")

        redis_config = copy.copy(self._config["redis"])
        host = redis_config.pop("host")
        port = redis_config.pop("port")

        return await aioredis.create_pool((host, port), **redis_config)

    async def setup(self) -> None:
        self._redis = await self._get_redis()
        self._queue = MessageQueue(self._redis, "queue:jobs")

    async def stop(self) -> None:
        self._redis.close()

    async def run(self) -> None:
        await self.setup()

        # a single loop so far, TODO
        while True:
            for msg in await self._queue.get(count=5, timeout=10):
                try:
                    job = Job.from_message(msg)
                except (UnknownJobError, MalformedPayloadError) as e:
                    log.warning(
                        "error pasing job: %s: %s", e.__class__.__name__, str(e)
                    )

                log.debug("scheduling job %s", job.type)
                await job.run(self._config)
