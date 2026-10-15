# 🚆 RailPulse • IRCTC Smart PNR & Waitlist Tracker (Hybrid Architecture)

A 100% zero-cost Full-Stack application for tracking IRCTC train ticket waitlists, calculating Confirmation Probability (%) using Quota & Coach capacity turnover algorithms, and dispatching real-time WhatsApp alerts upon berth movements.

---

## 🏗️ Clean Hybrid Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │             React Frontend (Vite)            │
                        │            http://localhost:5173             │
                        └──────────────────────┬───────────────────────┘
                                               │ (Vite /api proxy)
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │          Main Backend (Python FastAPI)       │
                        │             http://localhost:8000            │
                        │                                              │
                        │  • All REST APIs (/api/pnrs, /api/system...) │
                        │  • Real-Time SSE Stream (/api/stream)        │
                        │  • Confirmation Predictor (predictor.py)     │
                        │  • SQLite Database (pnr_tracker.db)          │
                        │  • APScheduler (5m intervals + 23:45 IST)    │
                        │  • Gemini 2.5 Flash Travel Intelligence      │
                        └─────────────▲──────────────────┬─────────────┘
                                      │                  │
                Incoming Webhook      │                  │ HTTP POST /send
           (TRACK <PNR> / STOP <PNR>) │                  │ (phone, message)
                                      │                  ▼
                        ┌─────────────┴────────────────────────────────┐
                        │   WhatsApp Bridge Microservice (Node.js)     │
                        │             http://localhost:3001            │
                        │                                              │
                        │  • @whiskeysockets/baileys Multi-Device      │
                        │  • GET /qr (Status & QR dataUrl for modal)   │
                        │  • POST /send (Dispatches WhatsApp message)  │
                        │  • POST /reconnect & POST /disconnect        │
                        │  • Forwards inbound commands to FastAPI      │
                        └──────────────────────────────────────────────┘
```

---

## 🌟 Key Features

### 1. ⚡ 100% Zero-Investment / Free Operation
- **Simulation Mode Active by Default:** Test waitlist drops, berth movements, and WhatsApp messages without spending a single RapidAPI credit.
- **Local SQLite Database (`pnr_tracker.db`):** Zero cloud database costs via SQLite in WAL mode.
- **Direct Baileys WhatsApp Engine (`@whiskeysockets/baileys`):** Connects directly to WhatsApp Multi-Device protocol without Twilio or paid API gateways.

### 2. 📱 WhatsApp Multi-Device Engine & In-Browser QR Scanner
- **Direct QR Display in Dashboard:** Click **"Scan QR to Connect 📱"** in the top navigation bar to scan the Baileys QR code right from your phone.
- **Two-Way Bot Commands:**
  - `TRACK <10-digit-PNR>`: Activates instant waitlist tracking & movement alerts.
  - `STOP <10-digit-PNR>`: Pauses notifications for the ticket.
  - `STATUS <PNR>`: Returns current live status and confirmation odds.
  - `HELP`: Displays bot instructions.

### 3. 🎯 Confirmation Probability Engine (`predictor.py`)
Calculates a Bayesian confirmation percentage (0% to 99%) and Risk Badges (`High Chance`, `Moderate`, `High Risk`):
- **Quota Weighting:** `GNWL` (highest base clearance), `RAC` (95%+ guaranteed boarding), `RLWL` (moderate), `PQWL` (low), `TQWL` (very low due to non-refundable Tatkal).
- **Class Turnover Weighting:** `SL` (10-14 coaches) & `3A` (6-11 coaches) have higher turnover than `1A` or `2A`.
- **Time-to-Departure Velocity:** Adjusts odds based on hours remaining until departure and chart preparation.
- **Optional Gemini 2.5 Flash:** Generates expert Indian Railways travel advice.

### 4. 🌙 Smart APScheduler & Strict Diff Engine
- **IRCTC Night Maintenance Window Awareness:** Automatically pauses polling during **11:45 PM – 12:30 AM IST (23:45–00:30 IST)** to prevent API locks.
- **Strict Diffing:** Only alerts when waitlist numbers change or when `chart_prepared` flips to `true` (zero notification spam).
- **Rich WhatsApp Notification Format:**
  ```text
  🚆 *IRCTC Waitlist Movement Alert!*
  🎫 *PNR:* 2458910342
  🚄 *Train:* 12952 - New Delhi Tejas Rajdhani (3A)

  📉 *Previous Status:* GNWL 24
  📈 *Current Status:* *GNWL 18* (Moved up by 6!)
  🎯 *Confirmation Chance:* *84% (High Chance)*

  ⏳ *Next auto-check in:* 2 hours
  _Reply STOP 2458910342 to mute alerts._
  ```

### 5. 🎨 Dark-Mode Glassmorphic Dashboard
- **Perforated Railway Boarding Pass Cards:** Route header (`NDLS ➔ MMCT`), station names, train numbers, and journey details.
- **Circular Animated Probability Gauge:** Glowing SVG radial gauge color-coded Emerald Green (≥75%), Amber (45-74%), and Rose (<45%).
- **Waitlist Movement Sparkline / Timeline:** Step history showing every historical jump (e.g. `Booked: WL 42 ➔ WL 31 ➔ WL 24 ➔ WL 18 ▲ +6`).
- **Interactive Action Buttons:**
  - ⚡ **Simulate WL Drop (Test WhatsApp):** Triggers waitlist drop and WhatsApp dispatch without consuming RapidAPI credits.
  - 🎉 **Simulate CNF:** Confirms ticket and triggers confetti across the screen!
  - 🔄 **Force Check Now:** Re-queries ticket status.
  - ⏸️ **Pause / Resume Tracking**.
- **Live WhatsApp Notification Feed Sidebar:** WhatsApp-style chat drawer displaying recent alerts with delivery status.

---

## 🚀 Quickstart

### Start the Entire Ecosystem in One Command
```bash
npm run dev
# or: node start-dev.js
```

This concurrently launches:
1. **WhatsApp Baileys Microservice** on [http://localhost:3001](http://localhost:3001)
2. **FastAPI Main Backend** on [http://localhost:8000](http://localhost:8000)
3. **Vite React Frontend** on [http://localhost:5173](http://localhost:5173)

---

## 📁 Repository Structure

```
railpulse/
├── package.json               # Root scripts ("npm run dev")
├── start-dev.js               # Multi-service launcher (Bridge + FastAPI + Vite)
├── README.md                  # Complete documentation
├── whatsapp-bridge/           # [Node.js Microservice ~80 lines on Port 3001]
│   ├── package.json           # @whiskeysockets/baileys, express, qrcode
│   └── index.js               # GET /qr, POST /send, inbound webhook forwarder
├── backend/                   # [Main Python FastAPI Backend on Port 8000]
│   ├── requirements.txt       # fastapi, uvicorn, apscheduler, httpx, pydantic
│   ├── pnr_tracker.db         # SQLite local database (pre-seeded)
│   ├── main.py                # REST API routes, SSE stream & inbound webhook
│   ├── database.py            # SQLite schema, tables & seed data
│   ├── predictor.py           # Confirmation % calculator (Quota/Class/Time)
│   ├── pnr_simulator.py       # Simulation engine, drops, and Gemini OCR
│   └── scheduler.py           # APScheduler with 23:45-00:30 IST pause logic
└── client/                    # [Untouched Modern UI on Port 5173]
    ├── package.json           # Vite, React, Tailwind CSS, Framer Motion, Confetti
    ├── vite.config.js         # Proxy configuration pointing to :8000
    └── src/
        ├── App.jsx            # Real-time SSE reactivity
        └── components/
            ├── Navbar.jsx              # Status indicators & QR modal trigger
            ├── HeroQuickAdd.jsx        # PNR input, phone input & file drag-drop
            ├── TicketCard.jsx          # Perforated boarding pass ticket
            ├── ConfirmationGauge.jsx   # Glowing radial SVG probability meter
            ├── WhatsAppModal.jsx       # Baileys QR code connection modal
            └── NotificationSidebar.jsx # WhatsApp-style chat alert drawer
```
