from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

from core.database import get_db
from core.deps import get_current_user
from models.models import Product
from schemas.schemas import ProductCreate, ProductUpdate, ProductOut, AIDescriptionRequest, AIDescriptionResponse

router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

@router.get("/", response_model=List[ProductOut])
async def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """List all active products."""
    try:
        query = select(Product).where(Product.is_active == True)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        if category:
            query = query.where(Product.category == category)
        query = query.offset(skip).limit(limit).order_by(Product.name)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Create a new product."""
    try:
        # Check SKU uniqueness
        result = await db.execute(select(Product).where(Product.sku == data.sku))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SKU already exists")

        product = Product(**data.model_dump())
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Update a product."""
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
        return product
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Soft delete a product."""
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        product.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/generate-description", response_model=AIDescriptionResponse)
async def generate_ai_description(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Generate AI marketing description for a product using Claude API."""
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        description = await _call_claude_api(product.name, product.category)

        # Save the AI description to the product
        product.ai_description = description
        await db.commit()

        return AIDescriptionResponse(description=description)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-description/preview", response_model=AIDescriptionResponse)
async def preview_ai_description(
    data: AIDescriptionRequest,
    _: dict = Depends(get_current_user)
):
    """Generate AI description preview without saving."""
    try:
        description = await _call_claude_api(data.product_name, data.category)
        return AIDescriptionResponse(description=description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _call_claude_api(product_name: str, category: Optional[str] = None) -> str:
    """Call Claude API to generate a product description."""
    if not ANTHROPIC_API_KEY:
        # Fallback mock description if no API key
        return (
            f"{product_name} is a premium quality product designed to meet the highest industry standards. "
            f"Built for reliability and performance, it delivers exceptional value across diverse applications."
        )

    category_text = f" in the {category} category" if category else ""
    prompt = (
        f"Write a professional 2-sentence marketing description for a product called '{product_name}'{category_text}. "
        f"Make it compelling, concise, and highlight key benefits. Do not use bullet points."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            data = response.json()
            return data["content"][0]["text"].strip()
    except Exception:
        return (
            f"{product_name} is a premium quality product engineered to exceed expectations. "
            f"Combining superior craftsmanship with innovative design, it stands as the ideal choice for discerning professionals."
        )
