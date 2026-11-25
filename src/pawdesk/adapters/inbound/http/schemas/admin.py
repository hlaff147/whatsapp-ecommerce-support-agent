"""Schemas administrativos e LGPD."""

from pydantic import BaseModel


class AnonymizeRequest(BaseModel):
    phone: str | None = None
    channel_user_hash: str | None = None
