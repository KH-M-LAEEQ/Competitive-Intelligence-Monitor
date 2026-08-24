from datetime import datetime

from pydantic import BaseModel


class ResponseLibraryItemCreate(BaseModel):
    competitor_id: int | None = None
    title: str
    body_markdown: str
    tags: list[str] | None = None


class ResponseLibraryItemUpdate(BaseModel):
    title: str | None = None
    body_markdown: str | None = None
    tags: list[str] | None = None


class ResponseLibraryItemResponse(BaseModel):
    id: int
    workspace_id: int
    competitor_id: int | None = None
    title: str
    body_markdown: str
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
