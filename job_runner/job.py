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
import inspect

from typing import Any, Dict, Type, Awaitable, Optional
from secrets import token_urlsafe
from email.message import EmailMessage

from arpq import Message
from aiosmtplib import SMTP

from .context import Context

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
    SINGLE_USE_PASSWORD_EMAIL = 1


class Job:
    _job_map: Dict[int, Type[Job]] = {}

    _is_async: bool

    def __init_subclass__(cls, /, job_type: JobType = JobType.UNSSSIGNED) -> None:
        super().__init_subclass__()

        if job_type != JobType.UNSSSIGNED:
            if job_type.value in cls._job_map:
                raise TypeError(f"Duplicated job type: {job_type} in {cls}")

            cls._is_async = inspect.iscoroutinefunction(cls.run)
            cls._job_map[job_type.value] = cls

    def __init__(
        self, priority: int, job_type: JobType, created_at: float, **kwargs: Any
    ):
        self._priority = priority
        self._created_at = created_at
        self._job_type = job_type

    @classmethod
    def from_message(cls, msg: Message) -> Job:
        data = msg.data
        if "t" not in data:
            raise MalformedPayloadError

        if (job_cls := cls._job_map.get(data["t"])) is None:
            raise UnknownJobError

        job = job_cls(
            priority=msg.priority,
            job_type=data["t"],
            created_at=data.get("c", time.time()),
        )

        job.set_data(**data.get("d"))

        return job

    def set_data(self, **kwargs: Any) -> None:
        pass

    def run(self, ctx: Context) -> Optional[Awaitable[None]]:
        raise NotImplementedError

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def type(self) -> JobType:
        return self._job_type

    @property
    def is_async(self) -> bool:
        return self._is_async

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type} priority={self.priority} created_at={self.created_at}>"


class SendLocalizedEmailJob(Job, job_type=JobType.SEND_LOCALIZED_EMAIL):
    CONFIRMATION_TOKEN_BYTES = 20
    CONFIRMATION_TOKEN_TTL = 5 * 24 * 60 * 60  # 5 days

    SINGLE_USE_PASSWORD_BYTES = 15
    SINGLE_USE_PASSWORD_TTL = 5 * 24 * 60 * 60  # 5 days

    def set_data(  # type: ignore
        self, email_type: int, language: str, to: str, user_id: bytes, **kwargs: Any
    ) -> None:
        self._email_type = EmailType(email_type)
        self._to = to
        self._user_id = user_id

    async def _fill_email_confirmation_message(
        self, msg: EmailMessage, ctx: Context
    ) -> EmailMessage:
        confirmation_token = token_urlsafe(self.CONFIRMATION_TOKEN_BYTES)
        await ctx.redis.execute(
            "SET",
            f"confirmation:{confirmation_token}",
            self._user_id,
            "EX",
            self.CONFIRMATION_TOKEN_TTL,
        )

        # hardcoded, probably bad
        url = f"https://modbay.net/api/v0/auth/email/confirm/{confirmation_token}"

        msg["Subject"] = "TODO: localized subject of: email confirmation"
        msg.set_content(f"TODO: localized body of: email confirmation: {url}")

        return msg

    async def _fill_single_use_password_key_message(
        self, msg: EmailMessage, ctx: Context
    ) -> EmailMessage:
        single_use_password = token_urlsafe(self.SINGLE_USE_PASSWORD_BYTES)
        await ctx.redis.execute(
            "SET",
            f"single_use_password:{single_use_password}",
            self._user_id,
            "EX",
            self.SINGLE_USE_PASSWORD_TTL,
        )

        msg["Subject"] = "TODO: localized subject of: single use password"
        msg.set_content(
            f"TODO: localized body of: single use password: {single_use_password}"
        )

        return msg

    async def _fill_message(self, msg: EmailMessage, ctx: Context) -> EmailMessage:
        if self._email_type is EmailType.EMAIL_CONFIRMATION:
            msg = await self._fill_email_confirmation_message(msg, ctx)
        elif self._email_type is EmailType.SINGLE_USE_PASSWORD_EMAIL:
            msg = await self._fill_single_use_password_key_message(msg, ctx)

        return msg

    async def run(self, ctx: Context) -> None:
        msg = EmailMessage()

        mail_config = ctx.config["mail"]

        msg["From"] = mail_config["from"]
        msg["To"] = self._to

        async with SMTP(mail_config["server"], start_tls=True) as server:
            await server.login(
                mail_config["login"], mail_config["password"],
            )

            await server.send_message(await self._fill_message(msg, ctx))


class PrintJob(Job, job_type=JobType.PRINT):
    def set_data(self, text: str, **kwargs: Any) -> None:  # type: ignore
        self.text = text

    def run(self, ctx: Context) -> None:
        print(self.text)
