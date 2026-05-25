from typing import Literal

from pydantic import BaseModel


class InvalidateCacheRequest(BaseModel):
    scopes: list[Literal["search", "expand"]] = ["search", "expand"]
