from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.surface import SurfaceType


class SurfaceCreate(BaseModel):
    surface_type: SurfaceType = SurfaceType.other
    name: str | None = None
    url: HttpUrl
    check_frequency: str = "daily"
    capture_visual: bool = False


class SurfaceResponse(BaseModel):
    id: int
    competitor_id: int
    surface_type: SurfaceType
    name: str | None = None
    url: str
    check_frequency: str
    capture_visual: bool
    is_active: bool
    last_checked_at: datetime | None = None

    class Config:
        from_attributes = True
