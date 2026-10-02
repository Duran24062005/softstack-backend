from typing import Literal

from pydantic import BaseModel, Field


MediaKind = Literal["image", "video"]


class MediaReference(BaseModel):
    url: str = Field(min_length=1, max_length=2_048)
    pathname: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=120)
    size: int = Field(ge=1)


class ContentMediaImportRequest(BaseModel):
    source_url: str = Field(min_length=1, max_length=2_048)
    kind: MediaKind | None = None


class ContentMediaDeleteRequest(BaseModel):
    pathname: str = Field(min_length=1, max_length=512)
