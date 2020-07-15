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

import os
import asyncio
import logging

import uvloop
import sentry_sdk

from .config import CONFIG_FORMAT, Config
from .logger import setup as setup_logger
from .job_runner import JobRunner

uvloop.install()

log = logging.getLogger(__name__)


if __name__ == "__main__":
    setup_logger()

    log.info(f"running on version {os.environ.get('GIT_COMMIT', 'UNSET')}")

    config = Config(CONFIG_FORMAT)
    if config["sentry"]["enabled"]:
        log.info("initializing sentry")
        sentry_sdk.init(
            dsn=config["sentry"]["dsn"], send_default_pii=True,
        )
    else:
        log.info("skipping sentry initialization")

    job_runner = JobRunner(config)
    asyncio.run(job_runner.run())
