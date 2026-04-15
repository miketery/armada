import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductGunCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str
    msrp: Decimal = Field(..., ge=0)
    caliber: str = Field(..., max_length=50)
    action_type: str = Field(..., max_length=50)
    weight_lbs: Decimal = Field(..., gt=0)
    category: str = Field(..., max_length=50)
    manufacturer: str = Field(..., max_length=200)


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

    model_config = {"from_attributes": True}


class ProductGunResponse(ProductResponse):
    caliber: str
    action_type: str
    weight_lbs: Decimal
    category: str
    manufacturer: str
