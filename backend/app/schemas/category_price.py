from pydantic import BaseModel


class CategoryPriceRequest(BaseModel):
    category: str


class CategoryPriceResponse(BaseModel):
    category: str
    listing_url: str | None
    prices_found: int
    min_price: float | None
    max_price: float | None
    avg_price: float | None
    currency: str | None

    class Config:
        from_attributes = True
