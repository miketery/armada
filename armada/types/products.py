import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductImageCreate(BaseModel):
    url: str = Field(..., max_length=500)
    alt_text: str | None = Field(None, max_length=200)
    sort_order: int = 0


class ProductImageResponse(BaseModel):
    id: uuid.UUID
    url: str
    alt_text: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class ProductGunCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str
    msrp: Decimal = Field(..., ge=0)
    caliber: str = Field(..., max_length=50)
    action_type: str = Field(..., max_length=50)
    weight_lbs: Decimal = Field(..., gt=0)
    category: str = Field(..., max_length=50)
    manufacturer: str = Field(..., max_length=200)
    images: list[ProductImageCreate] = Field(default_factory=list)


class ProductGunUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    msrp: Decimal | None = Field(None, ge=0)
    caliber: str | None = Field(None, max_length=50)
    action_type: str | None = Field(None, max_length=50)
    weight_lbs: Decimal | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=50)
    manufacturer: str | None = Field(None, max_length=200)


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    msrp: Decimal
    product_type: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProductGunResponse(ProductResponse):
    caliber: str
    action_type: str
    weight_lbs: Decimal
    category: str
    manufacturer: str
