# 🏭 PO Management System
### ERP Micro-service — IV Innovations Private Limited

A full-stack Purchase Order Management System built with **FastAPI + PostgreSQL** backend and a dark-themed **Vanilla JS** frontend with JWT authentication and AI-powered product descriptions.

---

## 📁 Project Structure

```
po-management/
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── requirements.txt
│   ├── .env.example
│   ├── core/
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── security.py          # JWT creation/verification, bcrypt
│   │   └── deps.py              # FastAPI dependencies (auth guard)
│   ├── models/
│   │   └── models.py            # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py           # Pydantic v2 request/response schemas
│   ├── routers/
│   │   ├── auth.py              # /api/auth — register, login
│   │   ├── vendors.py           # /api/vendors — CRUD
│   │   ├── products.py          # /api/products — CRUD + AI description
│   │   └── purchase_orders.py  # /api/purchase-orders — CRUD + status flow
│   └── migrations/
│       └── migration.sql        # PostgreSQL schema + seed data
│
└── frontend/
    ├── index.html               # Dashboard
    ├── css/
    │   └── main.css             # Full dark-theme CSS system
    ├── js/
    │   └── api.js               # Centralised API client + auth helpers
    └── pages/
        ├── login.html           # Login + Register
        ├── purchase-orders.html # PO dashboard + Create PO modal
        ├── vendors.html         # Vendor management
        └── products.html        # Product catalog + AI descriptions
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Node.js (optional, for serving frontend)

---

### 1. Database Setup

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE po_management;"

# Run the migration + seed data
psql -U postgres -d po_management -f backend/migrations/migration.sql
```

---

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, and optionally ANTHROPIC_API_KEY

# Start the server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

### 3. Frontend Setup

```bash
# Option A: Python simple server (no install needed)
cd frontend
python -m http.server 3000

# Option B: Node live-server
npx live-server frontend --port=3000
```

Open `http://localhost:3000` in your browser.

**Demo credentials:**  
Email: `admin@iv-innovations.com`  
Password: `admin123`

---

## 🗄️ Database Design

### Schema Overview

```
users ──────────────────────────────────────────────
  id, email, full_name, hashed_password, is_active

vendors ─────────────────────────────────────────────
  id, name, contact_email, contact_phone, address, rating, is_active

products ────────────────────────────────────────────
  id, name, sku (UNIQUE), category, unit_price, stock_level, unit, 
  description, ai_description, is_active

purchase_orders ─────────────────────────────────────
  id, reference_no (UNIQUE), vendor_id (FK→vendors),
  status (ENUM), subtotal, tax_rate, tax_amount, total_amount,
  notes, created_by

purchase_order_items ────────────────────────────────
  id, purchase_order_id (FK→purchase_orders CASCADE DELETE),
  product_id (FK→products), quantity, unit_price, line_total
```

### Design Decisions

**Why separate `unit_price` in `purchase_order_items`?**  
Product prices change over time. Storing the price at the time of order creation ensures historical accuracy — a PO's total never changes retroactively.

**Why soft-delete vendors and products?**  
Existing POs reference these entities. Hard deletion would break referential integrity and historical records. Soft delete (`is_active = false`) preserves data while removing from active lists.

**Why `tax_rate` stored on the PO?**  
Tax rates are policy-driven and can change. Storing it per-order ensures the calculation is always reproducible.

**Status state machine:**
```
DRAFT → PENDING → APPROVED → RECEIVED
  ↓         ↓         ↓
CANCELLED CANCELLED CANCELLED
```
Only DRAFT orders can be deleted.

---

## 💡 Business Logic

### Calculate Total (5% Tax)
**File:** `backend/routers/purchase_orders.py` → `calculate_totals()`

```python
def calculate_totals(items):
    subtotal    = sum(item.line_total for item in items)
    tax_amount  = round(subtotal * 0.05, 2)   # 5% GST
    total_amount = round(subtotal + tax_amount, 2)
    return { "subtotal", "tax_amount", "total_amount" }
```

This function is called on every PO creation. The frontend also mirrors this logic live as the user adds/modifies rows.

### Add Row Logic (Frontend)
**File:** `frontend/pages/purchase-orders.html` → `addItemRow()`

Each call to `addItemRow()` creates a new DOM row with:
- A `<select>` of all products (populated via API)
- Quantity and price inputs (price auto-fills from product data)
- Live line total that recalculates on any input change
- A remove button (minimum 1 row enforced)

The `updateTotals()` function scans all rows and mirrors the backend tax calculation in real time.

---

## 🤖 Gen AI Integration

### How It Works
The `POST /api/products/{id}/generate-description` endpoint sends the product name and category to the **Claude API** (`claude-haiku-4-5`) with a prompt asking for a 2-sentence marketing description.

If no `ANTHROPIC_API_KEY` is set, a professional fallback description is returned so the app stays functional without an API key.

The generated description is:
1. Returned in the API response
2. Saved to `products.ai_description` in PostgreSQL
3. Displayed on the product card and in the create-product form (preview mode)

---

## 🔐 Authentication

JWT-based auth using `python-jose` + `passlib[bcrypt]`.

- `POST /api/auth/register` — creates a new user
- `POST /api/auth/login` — returns a Bearer token (8-hour expiry)
- All other endpoints require `Authorization: Bearer <token>`

The frontend stores the token in `localStorage` and injects it via the `API._request()` wrapper. On 401, it auto-redirects to the login page.

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/vendors/` | List vendors |
| POST | `/api/vendors/` | Create vendor |
| PUT | `/api/vendors/{id}` | Update vendor |
| DELETE | `/api/vendors/{id}` | Soft-delete vendor |
| GET | `/api/products/` | List products |
| POST | `/api/products/` | Create product |
| POST | `/api/products/{id}/generate-description` | AI description |
| GET | `/api/purchase-orders/` | List POs (filterable) |
| POST | `/api/purchase-orders/` | Create PO (auto-calculates tax) |
| PATCH | `/api/purchase-orders/{id}/status` | Update PO status |
| DELETE | `/api/purchase-orders/{id}` | Delete DRAFT PO |

Full interactive documentation available at `http://localhost:8000/docs`

---

## ⭐ Bonus Features Implemented

- **AI Integration** — Claude API for product descriptions (with graceful fallback)
- **Status State Machine** — validated transitions (Draft→Pending→Approved→Received)
- **Live Total Calculation** — frontend mirrors backend 5% tax logic in real-time
- **Soft Deletes** — preserves referential integrity for historical POs
- **Async SQLAlchemy** — full async/await for high performance
- **Pydantic v2** — modern validation with `model_config = ConfigDict(from_attributes=True)`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 14, asyncpg driver |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Frontend | Vanilla JS, HTML5, CSS3 (no framework) |
| AI | Anthropic Claude API (claude-haiku-4-5) |
| Fonts | Syne, DM Sans, JetBrains Mono (Google Fonts) |
