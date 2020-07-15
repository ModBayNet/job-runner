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

import enum
import time

from typing import Any, Dict, Type, Tuple
from email.message import EmailMessage

from arpq import Message
from aiosmtplib import SMTP

from .config import Config

PRIORITY_LOW = 1
PRIORITY_MEDIUM = 10
PRIORITY_HIGH = 20


class MalformedPayloadError(Exception):
    pass


class UnknownJobError(Exception):
    pass


class JobType(enum.Enum):
    UNSSSIGNED = -1
    SEND_LOCALIZED_EMAIL = 0
    PRINT = 666


class EmailType(enum.Enum):
    EMAIL_CONFIRMATION = 0


# TODO: use typevar for typing
class JobMeta(type):
    _job_map: Dict[int, Type[Job]] = {}

    def __init__(cls: type, name: str, bases: Tuple[type, ...], dct: Dict[str, Any]):
        if not hasattr(cls, "job_type"):
            raise RuntimeError(f"{name}: does not have job_type property")

        job_type = cls.job_type  # type: ignore
        job_map = cls._job_map  # type: ignore
        if job_type != JobType.UNSSSIGNED:
            if job_type in job_map:
                raise TypeError(f"Duplicated job type: {job_type} in {name}")

            job_map[job_type.value] = cls

    @classmethod
    def get_job_by_type(mcls, job_type: int) -> Type[Job]:
        if job_type not in mcls._job_map:
            raise UnknownJobError

        return mcls._job_map[job_type]


class Job(metaclass=JobMeta):
    job_type = JobType.UNSSSIGNED

    def __init__(self, priority: int, created_at: float = None, **kwargs: Any):
        self._priority = priority

        self._created_at = time.time() if created_at is None else created_at

    @classmethod
    def from_message(cls, msg: Message) -> Job:
        data = msg.data
        if "t" not in data:
            raise MalformedPayloadError

        job_cls = type(cls).get_job_by_type(data["t"])

        job = job_cls(
            priority=msg.priority, job_type=data.get("t"), created_at=data.get("c"),
        )

        job.set_data(**data.get("d"))

        return job

    def set_data(self, **kwargs: Any) -> None:
        pass

    async def run(self, config: Config) -> None:
        raise NotImplementedError

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def type(self) -> JobType:
        return self.job_type

    @property
    def created_at(self) -> float:
        return self._created_at

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type} priority={self.priority} created_at={self.created_at}>"


class SendLocalizedEmailJob(Job):
    job_type = JobType.SEND_LOCALIZED_EMAIL

    def set_data(  # type: ignore
        self, email_type: int, language: str, to: str, url: str, **kwargs: Any
    ) -> None:
        self._email_type = EmailType(email_type)
        self._to = to
        self._url = url

    def _fill_message(self, msg: EmailMessage) -> EmailMessage:
        if self._email_type is EmailType.EMAIL_CONFIRMATION:
            msg["Subject"] = "TODO: localized subject of: confirmation link"
            msg.set_content(f"TODO: localized body of: confirmation link: {self._url}")

        return msg

    async def run(self, config: Config) -> None:
        msg = EmailMessage()
        msg["From"] = config["mail"]["from"]
        msg["To"] = self._to

        async with SMTP(config["mail"]["server"], start_tls=True) as server:
            await server.login(
                config["mail"]["login"], config["mail"]["password"],
            )

            await server.send_message(self._fill_message(msg))


class PrintJob(Job):
    job_type = JobType.PRINT

    def set_data(self, text: str, **kwargs: Any) -> None:  # type: ignore
        self.text = text

    async def run(self, config: Config) -> None:
        print(self.text)
