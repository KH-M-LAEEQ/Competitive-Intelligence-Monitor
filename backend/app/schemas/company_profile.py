from datetime import datetime

from pydantic import BaseModel


class KeyPerson(BaseModel):
    name: str
    title: str


class CompanyProfileUpsert(BaseModel):
    industry: str | None = None
    hq_location: str | None = None
    employee_range: str | None = None
    funding_stage: str | None = None
    key_people: list[KeyPerson] | None = None
    notes_markdown: str | None = None
    website_domain: str | None = None


class CompanyProfileResponse(BaseModel):
    id: int
    competitor_id: int
    industry: str | None = None
    hq_location: str | None = None
    employee_range: str | None = None
    funding_stage: str | None = None
    key_people: list[KeyPerson] | None = None
    notes_markdown: str | None = None
    website_domain: str | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
