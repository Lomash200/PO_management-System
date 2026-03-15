from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from models.models import POStatus


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Vendor Schemas ──────────────────────────────────────────────────────────

class VendorBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    rating: float = Field(default=0.0, ge=0.0, le=5.0)

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_active: Optional[bool] = None

class VendorOut(VendorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


# ─── Product Schemas ─────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    sku: str = Field(min_length=2, max_length=100)
    category: Optional[str] = None
    unit_price: float = Field(gt=0)
    stock_level: int = Field(default=0, ge=0)
    unit: str = "unit"
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, gt=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    unit: Optional[str] = None
    description: Optional[str] = None
    ai_description: Optional[str] = None
    is_active: Optional[bool] = None

class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ai_description: Optional[str] = None
    is_active: bool
    created_at: datetime


# ─── Purchase Order Schemas ───────────────────────────────────────────────────

class POItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Optional[float] = Field(default=None, gt=0)  # Optional override

class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float
    product: ProductOut

class PurchaseOrderCreate(BaseModel):
    vendor_id: int
    items: List[POItemCreate] = Field(min_length=1)
    notes: Optional[str] = None

class PurchaseOrderUpdate(BaseModel):
    status: Optional[POStatus] = None
    notes: Optional[str] = None

class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_no: str
    vendor_id: int
    status: POStatus
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    vendor: VendorOut
    items: List[POItemOut]


# ─── AI Description Schema ────────────────────────────────────────────────────

class AIDescriptionRequest(BaseModel):
    product_name: str
    category: Optional[str] = None

class AIDescriptionResponse(BaseModel):
    description: str
