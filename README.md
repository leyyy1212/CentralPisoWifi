# Central PisoWiFi Server

A commercial-grade PisoWiFi management platform built with Flask and Supabase.

## Project Structure

```
CentralPisoWifi/
├── app.py                  # Main Flask application
├── config.py               # Supabase client
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── routes/
│   ├── auth.py             # POST /login
│   ├── voucher.py          # GET /voucher, POST /buy-voucher
│   ├── session.py          # POST /logout, /heartbeat, /consume
│   ├── hotspot.py          # GET /hotspot
│   └── admin.py            # GET /dashboard
│
├── services/
│   ├── voucher_service.py  # Voucher business logic
│   ├── session_service.py  # Session business logic
│   └── hotspot_service.py  # Hotspot business logic
│
├── database/
│   └── schema.sql          # Full Supabase schema
│
├── static/
└── templates/
```

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# 4. Apply database schema
# Open Supabase SQL Editor and run database/schema.sql

# 5. Run the server
python app.py
```

## API Endpoints

| Method | Route | Status | Description |
|--------|-------|--------|-------------|
| GET | / | ✅ Done | Health check |
| POST | /login | ✅ Done | Validate and login with voucher |
| GET | /voucher/<code> | ✅ Done | Get voucher details |
| POST | /buy-voucher | 🔄 Phase 3 | Purchase a voucher |
| POST | /logout | 🔄 Phase 3 | End a session |
| POST | /heartbeat | 🔄 Phase 3 | Keep session alive |
| POST | /consume | 🔄 Phase 3 | Deduct minutes |
| GET | /dashboard | 🔄 Phase 4 | Admin dashboard |

## Phases

- ✅ Phase 1 — Project setup (Flask + Supabase)
- ✅ Phase 2 — Database design + project structure
- 🔄 Phase 3 — Full REST API
- ⏳ Phase 4 — Admin Dashboard
- ⏳ Phase 5 — Hotspot Client Software
- ⏳ Phase 6 — Cloud Deployment
