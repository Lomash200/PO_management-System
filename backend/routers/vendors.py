from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from core.database import get_db
from core.deps import get_current_user
from models.models import Vendor
from schemas.schemas import VendorCreate, VendorUpdate, VendorOut

router = APIRouter()


@router.get("/", response_model=List[VendorOut])
async def list_vendors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """List all active vendors."""
    try:
        query = select(Vendor).where(Vendor.is_active == True)
        if search:
            query = query.where(Vendor.name.ilike(f"%{search}%"))
        query = query.offset(skip).limit(limit).order_by(Vendor.name)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Get a vendor by ID."""
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    data: VendorCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Create a new vendor."""
    try:
        vendor = Vendor(**data.model_dump())
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)
        return vendor
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{vendor_id}", response_model=VendorOut)
async def update_vendor(
    vendor_id: int,
    data: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Update a vendor."""
    try:
        result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(vendor, field, value)

        await db.commit()
        await db.refresh(vendor)
        return vendor
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Soft delete a vendor."""
    try:
        result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        vendor.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
