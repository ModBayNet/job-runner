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

from __future__ import annotations

import os
import sys
import logging

from typing import Any, Dict, Mapping

from ruamel.yaml import YAML

log = logging.getLogger(__name__)

DEFAULT_FILENAME = "config.yml"

CONFIG_FORMAT = {
    "logging": {"level": str},
    "mail": {"server": str, "from": str, "login": str, "password": str},
    "redis": {"host": str, "port": int, "db": int, "password": str},
    "sentry": {"enabled": bool, "dsn": str},
}


class _Empty:
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


_EMPTY = _Empty()
ENV_PREFIX = "MODBAY_"


class EnvTag:
    yaml_tag = "!env"

    @staticmethod
    def from_yaml(constructor: EnvTag, node: Any) -> str:
        if node.value not in os.environ:
            log.warn(f"{node.value} env variable is missing, using ''")

        return os.environ.get(node.value, "")


class Config:
    def __init__(self, config_format: Mapping[str, Any]) -> None:
        config = self._read_file()

        self._data = self.validate(config, config_format)

    @staticmethod
    def _read_file() -> Any:
        path = DEFAULT_FILENAME

        if not os.path.exists(path):
            log.critical(
                f"Config file {os.path.relpath(path)} is missing. "
                f"Example config file is located at {os.path.join(os.path.relpath('.'), 'config.example.yaml')}"
            )

            sys.exit(1)

        yaml = YAML(typ="safe")
        yaml.register_class(EnvTag)

        with open(path, "r") as f:
            return yaml.load(f)

    @staticmethod
    def validate(config: Any, config_format: Mapping[str, Any]) -> Any:
        """Validate config."""

        fixed_config = Config._fix_missing(config, config_format)

        return Config._validate(fixed_config, config_format)

    @staticmethod
    def _fix_missing(cfg: Any, fmt: Any, *path: str) -> Any:
        """Check for missing config keys and use default value when needed."""

        # node
        if isinstance(fmt, dict):
            filled_node: Dict[str, Any] = {}
            for name, node in fmt.items():
                # entire node is missing
                if cfg is _EMPTY:
                    cfg = {}

                filled_node[name] = Config._fix_missing(
                    cfg.get(name, _EMPTY), node, *path, name
                )

            return filled_node

        # leaf
        return cfg

    @staticmethod
    def _validate(cfg: Any, fmt: Any, *path: str) -> Any:
        """Validate config using format."""

        # leaf
        if not isinstance(cfg, dict):
            log.debug(f"{'.'.join(path)}: converting '{cfg}' -> {fmt}")

            if cfg is _EMPTY:
                log.warning(
                    f"{'.'.join(path)} key is missing from config/env, using ''"
                )
                return ""

            try:
                return fmt(cfg)
            except Exception as e:
                log.critical(f"Failed to convert {'.'.join(path)} to type {cfg}: {e}")

                sys.exit(1)

        # node
        validated_node = {}
        for name, node in cfg.items():
            if name not in fmt:
                log.warn(f"Unknown config key: {'.'.join([*path, name])}")

                continue

            validated_node[name] = Config._validate(node, fmt[name], *path, name)

        return validated_node

    def __getitem__(self, key: str) -> Any:
        return self._data[key]
