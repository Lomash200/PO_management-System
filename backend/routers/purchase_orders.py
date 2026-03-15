from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import random
import string
from datetime import datetime

from core.database import get_db
from core.deps import get_current_user
from models.models import PurchaseOrder, PurchaseOrderItem, Product, POStatus
from schemas.schemas import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderOut

router = APIRouter()

TAX_RATE = 0.05  # 5% tax


def generate_reference_no() -> str:
    """Generate unique PO reference number like PO-2024-XXXXX."""
    year = datetime.now().year
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PO-{year}-{suffix}"


def calculate_totals(items: list) -> dict:
    """
    Business Logic: Calculate subtotal, 5% tax, and total amount.
    Returns dict with subtotal, tax_amount, and total_amount.
    """
    subtotal = sum(item.line_total for item in items)
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return {
        "subtotal": round(subtotal, 2),
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


@router.get("/", response_model=List[PurchaseOrderOut])
async def list_purchase_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    status: Optional[POStatus] = None,
    vendor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """List all purchase orders with filters."""
    try:
        query = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
            )
        )
        if status:
            query = query.where(PurchaseOrder.status == status)
        if vendor_id:
            query = query.where(PurchaseOrder.vendor_id == vendor_id)
        query = query.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{po_id}", response_model=PurchaseOrderOut)
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Get a purchase order by ID."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
        )
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.post("/", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new purchase order.
    Business Logic: Automatically calculates 5% tax and total amount.
    """
    try:
        # Validate vendor exists
        vendor_result = await db.execute(
            select(PurchaseOrder.__table__.c.vendor_id)
            .where(PurchaseOrder.vendor_id == data.vendor_id)
            .limit(1)
        )

        # Build PO items with validated prices
        po_items = []
        for item_data in data.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item_data.product_id, Product.is_active == True)
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product ID {item_data.product_id} not found or inactive"
                )

            unit_price = item_data.unit_price if item_data.unit_price else product.unit_price
            line_total = round(unit_price * item_data.quantity, 2)

            po_items.append(PurchaseOrderItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                line_total=line_total,
            ))

        # Calculate totals with 5% tax
        totals = calculate_totals(po_items)

        # Create PO
        po = PurchaseOrder(
            reference_no=generate_reference_no(),
            vendor_id=data.vendor_id,
            notes=data.notes,
            created_by=current_user.get("sub", "system"),
            tax_rate=TAX_RATE,
            **totals
        )
        db.add(po)
        await db.flush()  # Get po.id before adding items

        for item in po_items:
            item.purchase_order_id = po.id
            db.add(item)

        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
            )
            .where(PurchaseOrder.id == po.id)
        )
        return result.scalar_one()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{po_id}/status", response_model=PurchaseOrderOut)
async def update_po_status(
    po_id: int,
    data: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Update purchase order status."""
    try:
        result = await db.execute(
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
            )
            .where(PurchaseOrder.id == po_id)
        )
        po = result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # Status transition validation
        valid_transitions = {
            POStatus.DRAFT: [POStatus.PENDING, POStatus.CANCELLED],
            POStatus.PENDING: [POStatus.APPROVED, POStatus.CANCELLED],
            POStatus.APPROVED: [POStatus.RECEIVED, POStatus.CANCELLED],
            POStatus.RECEIVED: [],
            POStatus.CANCELLED: [],
        }

        if data.status and data.status not in valid_transitions.get(po.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {po.status} to {data.status}"
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(po, field, value)

        await db.commit()
        await db.refresh(po)
        return po
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Delete a DRAFT purchase order only."""
    try:
        result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
        po = result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        if po.status != POStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Only DRAFT orders can be deleted")
        await db.delete(po)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
