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

import logging.config

from .cli import args
from .config import Config

LEVEL_TO_COLOR_VALUE = {
    "INFO": "32",  # green
    "WARNING": "33",  # yellow
    "ERROR": "31",  # red
    "CRITICAL": "41",  # white on red
}

COLOR_START = "\033["
COLOR_RESET = "\033[0m"

VERBOSE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
SIMPLE_FORMAT = "%(levelname)-8s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)

        color_value = LEVEL_TO_COLOR_VALUE.get(record.levelname)
        if color_value is None:
            return formatted

        return f"{COLOR_START}{color_value}m{formatted}{COLOR_RESET}"


def get_level(config: Config) -> int:
    if args.verbosity is not None:
        level = logging.getLevelName(args.verbosity.upper())
    else:
        level = logging.getLevelName(config["logging"]["level"].upper())

    if isinstance(level, int):
        return level

    raise ValueError(f"Unknown logging level passed: {level}")


def setup(config: Config) -> None:
    level = get_level(config)

    LOGGING_CONFIG = {
        "version": 1,
        "formatters": {
            "verbose": {"format": VERBOSE_FORMAT, "datefmt": DATE_FORMAT},
            "simple": {"format": SIMPLE_FORMAT},
            "colorful_verbose": {
                "()": ColorFormatter,
                "format": VERBOSE_FORMAT,
                "datefmt": DATE_FORMAT,
            },
            "colorful_simple": {"()": ColorFormatter, "format": SIMPLE_FORMAT},
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "simple",
            },
            "colorful_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "colorful_simple",
            },
        },
        "root": {"level": level, "handlers": ["colorful_console"]},
        "disable_existing_loggers": False,
    }

    logging.config.dictConfig(LOGGING_CONFIG)
