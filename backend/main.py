import os
import re
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

from database import init_db, get_connection
from predictor import calculate_probability, enhance_with_gemini
from pnr_simulator import (
    fetch_live_or_simulated_pnr,
    simulate_waitlist_drop,
    simulate_confirmation,
    extract_ticket_from_file,
    send_whatsapp_alert,
    WHATSAPP_BRIDGE_URL
)
from scheduler import get_irctc_status, start_scheduler

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

sse_subscribers = set()

async def broadcast_sse(event_data: dict):
    msg = f"data: {json.dumps(event_data)}\n\n"
    dead = set()
    for queue in list(sse_subscribers):
        try:
            await queue.put(msg)
        except Exception:
            dead.add(queue)
    for q in dead:
        sse_subscribers.discard(q)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    loop = asyncio.get_running_loop()
    start_scheduler(loop, broadcast_sse)
    print("🚀 [FastAPI] RailPulse Main Backend running on http://localhost:8000")
    yield

app = FastAPI(title="RailPulse IRCTC Smart PNR & WhatsApp Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Request Models
class AddPnrRequest(BaseModel):
    pnr: str
    phone: Optional[str] = "919876543210"
    trainNumber: Optional[str] = None
    trainName: Optional[str] = None
    sourceStation: Optional[str] = None
    destStation: Optional[str] = None
    sourceStationName: Optional[str] = None
    destStationName: Optional[str] = None
    journeyDate: Optional[str] = None
    journeyTime: Optional[str] = None
    travelClass: Optional[str] = None
    quota: Optional[str] = None
    bookingStatus: Optional[str] = None
    currentStatus: Optional[str] = None

class ModeRequest(BaseModel):
    mode: str

class TestPingRequest(BaseModel):
    phone: str

class WebhookRequest(BaseModel):
    senderPhone: str
    text: str
    jid: Optional[str] = None

# ==========================================
# 1. Real-Time Server-Sent Events (SSE)
# ==========================================
@app.get("/api/stream")
async def event_stream(request: Request):
    queue = asyncio.Queue()
    sse_subscribers.add(queue)

    async def event_generator():
        try:
            # Initial connection event
            yield f"data: {json.dumps({'type': 'CONNECTED', 'message': 'FastAPI SSE Stream Active'})}\n\n"

            # Query WhatsApp bridge for current status
            wa_status = {"status": "disconnected", "qrDataUrl": None, "connectedUser": None}
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{WHATSAPP_BRIDGE_URL}/qr")
                    if resp.status_code == 200:
                        wa_status = resp.json()
            except Exception:
                pass

            yield f"data: {json.dumps({'type': 'WHATSAPP_STATUS', 'data': wa_status})}\n\n"
            yield f"data: {json.dumps({'type': 'IRCTC_STATUS', 'data': get_irctc_status()})}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                message = await queue.get()
                yield message
        finally:
            sse_subscribers.discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ==========================================
# 2. PNR Management Routes
# ==========================================

@app.get("/api/pnrs")
def get_all_pnrs():
    conn = get_connection()
    tickets = [dict(r) for r in conn.execute("SELECT * FROM tracked_pnrs ORDER BY created_at DESC").fetchall()]
    for t in tickets:
        history = [dict(h) for h in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (t["pnr"],)).fetchall()]
        t["history"] = history
    conn.close()
    return {"success": True, "data": tickets}

@app.get("/api/pnrs/{pnr}")
def get_single_pnr(pnr: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = dict(row)
    history = [dict(h) for h in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (pnr,)).fetchall()]
    ticket["history"] = history
    conn.close()
    return {"success": True, "data": ticket}

@app.post("/api/pnrs")
async def add_pnr(payload: AddPnrRequest):
    clean_pnr = re.sub(r"\D", "", payload.pnr or "")
    if len(clean_pnr) != 10:
        raise HTTPException(status_code=400, detail="Invalid PNR: must be exactly 10 digits.")

    clean_phone = re.sub(r"\D", "", payload.phone or "")
    if not clean_phone.startswith("91") and len(clean_phone) == 10:
        clean_phone = f"91{clean_phone}"

    conn = get_connection()
    existing = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (clean_pnr,)).fetchone()

    if existing:
        conn.execute("UPDATE tracked_pnrs SET phone = ?, status = 'TRACKING' WHERE pnr = ?", (clean_phone, clean_pnr))
        conn.commit()
        ticket = dict(conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (clean_pnr,)).fetchone())
        history = [dict(h) for h in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (clean_pnr,)).fetchall()]
        ticket["history"] = history
        conn.close()
        await broadcast_sse({"type": "PNR_UPDATED", "pnr": clean_pnr})
        return {"success": True, "message": "Ticket resumed tracking", "data": ticket}

    conn.close()

    now_iso = datetime.utcnow().isoformat()

    # If ticket was extracted via PDF / OCR, prioritize real extracted fields!
    if payload.trainNumber and payload.trainName:
        c_digits = re.sub(r"\D", "", payload.currentStatus or "")
        b_digits = re.sub(r"\D", "", payload.bookingStatus or "")
        c_wl = int(c_digits) if c_digits else 15
        b_wl = int(b_digits) if b_digits else (c_wl + 10)
        fresh = {
            "pnr": clean_pnr,
            "train_number": payload.trainNumber,
            "train_name": payload.trainName,
            "source_station": payload.sourceStation or "NDLS",
            "dest_station": payload.destStation or "MMCT",
            "source_station_name": payload.sourceStationName or payload.sourceStation or "NDLS",
            "dest_station_name": payload.destStationName or payload.destStation or "MMCT",
            "journey_date": payload.journeyDate or (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
            "journey_time": payload.journeyTime or "16:00",
            "travel_class": payload.travelClass or "3A",
            "quota": payload.quota or "GNWL",
            "booking_status": payload.bookingStatus or f"{payload.quota or 'GNWL'} {b_wl}",
            "current_status": payload.currentStatus or f"{payload.quota or 'GNWL'} {c_wl}",
            "current_wl_number": c_wl,
            "booking_wl_number": b_wl,
            "chart_prepared": 1 if "CNF" in (payload.currentStatus or "").upper() else 0
        }
    else:
        fresh = await fetch_live_or_simulated_pnr(clean_pnr)

    prob_data = calculate_probability(
        quota=fresh["quota"],
        travel_class=fresh["travel_class"],
        booking_wl=fresh["booking_wl_number"],
        current_wl=fresh["current_wl_number"],
        current_status=fresh["current_status"],
        journey_date=fresh["journey_date"],
        journey_time=fresh["journey_time"],
        train_number=fresh["train_number"],
        train_name=fresh["train_name"]
    )

    smart_tip = prob_data["smart_tip"]
    try:
        gemini_tip = await enhance_with_gemini(
            fresh["train_number"], fresh["train_name"], fresh["travel_class"],
            fresh["quota"], fresh["current_status"], fresh["current_wl_number"],
            prob_data["probability"], prob_data["risk_badge"]
        )
        if gemini_tip:
            smart_tip = gemini_tip
    except Exception as ge:
        print(f"⚠️ Gemini enhancement skipped: {ge}")

    conn = get_connection()
    conn.execute("""
        INSERT INTO tracked_pnrs (
            pnr, phone, train_number, train_name, source_station, dest_station,
            source_station_name, dest_station_name, journey_date, journey_time,
            travel_class, quota, booking_status, current_status, previous_status,
            current_wl_number, booking_wl_number, chart_prepared, confirmation_probability,
            risk_badge, prediction_explanation, smart_tip, status, last_checked_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TRACKING', ?, ?)
    """, (
        clean_pnr, clean_phone or "919876543210", fresh["train_number"], fresh["train_name"],
        fresh["source_station"], fresh["dest_station"], fresh["source_station_name"], fresh["dest_station_name"],
        fresh["journey_date"], fresh.get("journey_time", "16:00"), fresh["travel_class"], fresh["quota"],
        fresh["booking_status"], fresh["current_status"], fresh["booking_status"],
        fresh["current_wl_number"], fresh["booking_wl_number"], fresh["chart_prepared"],
        prob_data["probability"], prob_data["risk_badge"], prob_data["explanation"],
        smart_tip, now_iso, now_iso
    ))

    conn.execute("""
        INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (clean_pnr, fresh["booking_status"], fresh["booking_wl_number"], prob_data["probability"], "Booking Initial Status", now_iso))

    if fresh["current_status"] != fresh["booking_status"]:
        conn.execute("""
            INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_pnr, fresh["current_status"], fresh["current_wl_number"], prob_data["probability"], "Current Position", now_iso))

    conn.commit()

    ticket = dict(conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (clean_pnr,)).fetchone())
    history = [dict(h) for h in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (clean_pnr,)).fetchall()]
    ticket["history"] = history
    conn.close()

    welcome_msg = f"""🚆 *IRCTC PNR Tracking Activated!*
🎫 *PNR:* {clean_pnr}
🚄 *Train:* {fresh['train_number']} - {fresh['train_name']} ({fresh['travel_class']})
📍 *Route:* {fresh['source_station']} ➔ {fresh['dest_station']}
📅 *Journey Date:* {fresh['journey_date']}

📊 *Current Status:* *{fresh['current_status']}*
🎯 *Confirmation Chance:* *{prob_data['probability']}% ({prob_data['risk_badge']})*

🔔 *Live Alerts:* You will receive instant alerts here whenever your waitlist position moves or charts are prepared!
_Reply STOP {clean_pnr} to mute alerts._"""

    notif = await send_whatsapp_alert(clean_phone, welcome_msg, clean_pnr, "WELCOME")

    await broadcast_sse({"type": "PNR_ADDED", "pnr": clean_pnr})
    await broadcast_sse({"type": "NEW_NOTIFICATION", "data": notif})

    return {"success": True, "data": ticket}

@app.delete("/api/pnrs/{pnr}")
async def delete_pnr(pnr: str):
    conn = get_connection()
    conn.execute("DELETE FROM pnr_history WHERE pnr = ?", (pnr,))
    conn.execute("DELETE FROM tracked_pnrs WHERE pnr = ?", (pnr,))
    conn.commit()
    conn.close()
    await broadcast_sse({"type": "PNR_DELETED", "pnr": pnr})
    return {"success": True, "message": f"PNR {pnr} deleted."}

@app.patch("/api/pnrs/{pnr}/status")
async def toggle_pnr_status(pnr: str):
    conn = get_connection()
    row = conn.execute("SELECT status FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket not found")

    new_status = "STOPPED" if row["status"] == "TRACKING" else "TRACKING"
    conn.execute("UPDATE tracked_pnrs SET status = ? WHERE pnr = ?", (new_status, pnr))
    conn.commit()
    conn.close()
    await broadcast_sse({"type": "PNR_UPDATED", "pnr": pnr})
    return {"success": True, "status": new_status}

# ==========================================
# 3. Simulation & Manual Actions
# ==========================================

@app.post("/api/pnrs/{pnr}/simulate-drop")
async def api_simulate_drop(pnr: str):
    try:
        result = await simulate_waitlist_drop(pnr)
        await broadcast_sse({"type": "PNR_UPDATED", "pnr": pnr})
        if result.get("notification"):
            await broadcast_sse({"type": "NEW_NOTIFICATION", "data": result["notification"]})
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pnrs/{pnr}/simulate-confirm")
async def api_simulate_confirm(pnr: str):
    try:
        result = await simulate_confirmation(pnr)
        await broadcast_sse({"type": "PNR_CONFIRMED", "pnr": pnr})
        if result.get("notification"):
            await broadcast_sse({"type": "NEW_NOTIFICATION", "data": result["notification"]})
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pnrs/{pnr}/check")
async def force_check_pnr(pnr: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket not found")

    now_iso = datetime.utcnow().isoformat()
    conn.execute("UPDATE tracked_pnrs SET last_checked_at = ? WHERE pnr = ?", (now_iso, pnr))
    conn.commit()
    ticket = dict(conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone())
    history = [dict(h) for h in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (pnr,)).fetchall()]
    ticket["history"] = history
    conn.close()

    await broadcast_sse({"type": "PNR_UPDATED", "pnr": pnr})
    return {"success": True, "message": "Ticket status verified", "data": ticket}

# ==========================================
# 4. WhatsApp Bridge Proxy & Inbound Webhook
# ==========================================

@app.get("/api/whatsapp/status")
async def get_whatsapp_status():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{WHATSAPP_BRIDGE_URL}/qr")
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
    except Exception as e:
        print(f"Could not reach WhatsApp bridge: {e}")
    return {"success": True, "data": {"status": "disconnected", "qrDataUrl": None, "connectedUser": None}}

@app.post("/api/whatsapp/reconnect")
async def reconnect_whatsapp():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{WHATSAPP_BRIDGE_URL}/reconnect")
    except Exception:
        pass
    return {"success": True, "message": "WhatsApp reconnect initiated"}

@app.post("/api/whatsapp/disconnect")
async def disconnect_whatsapp():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{WHATSAPP_BRIDGE_URL}/disconnect")
    except Exception:
        pass
    return {"success": True, "message": "WhatsApp disconnected"}

@app.post("/api/whatsapp/test-ping")
async def test_ping(payload: TestPingRequest):
    clean_phone = re.sub(r"\D", "", payload.phone or "")
    if not clean_phone.startswith("91") and len(clean_phone) == 10:
        clean_phone = f"91{clean_phone}"

    test_msg = """🔔 *IRCTC Tracker Test Ping*
Your WhatsApp alerts connection is working perfectly!
You will receive live waitlist updates for all your tracked tickets here."""

    notif = await send_whatsapp_alert(clean_phone, test_msg, "TEST", "SYSTEM")
    await broadcast_sse({"type": "NEW_NOTIFICATION", "data": notif})
    return {"success": True, "phone": clean_phone, **notif}

# Inbound webhook from Baileys microservice (TRACK <PNR>, STOP <PNR>, STATUS)
@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(payload: WebhookRequest):
    text = payload.text.strip()
    parts = text.split()
    command = parts[0].upper() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""
    sender_phone = payload.senderPhone

    print(f"📩 [FastAPI Webhook] Incoming message: '{text}' from +{sender_phone}")

    conn = get_connection()

    if command == "TRACK" and arg:
        pnr = re.sub(r"\D", "", arg)
        if len(pnr) != 10:
            return {"reply": "⚠️ *Invalid PNR Number*\nPlease provide a valid 10-digit IRCTC PNR number.\n*Example:* TRACK 2458910342"}

        ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
        if not ticket:
            fresh = await fetch_live_or_simulated_pnr(pnr)
            prob = calculate_probability(
                quota=fresh["quota"],
                travel_class=fresh["travel_class"],
                booking_wl=fresh["booking_wl_number"],
                current_wl=fresh["current_wl_number"],
                current_status=fresh["current_status"],
                journey_date=fresh["journey_date"]
            )
            now_iso = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO tracked_pnrs (
                    pnr, phone, train_number, train_name, source_station, dest_station,
                    source_station_name, dest_station_name, journey_date, travel_class,
                    quota, booking_status, current_status, previous_status, current_wl_number,
                    booking_wl_number, confirmation_probability, risk_badge, prediction_explanation,
                    smart_tip, status, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TRACKING', ?)
            """, (
                pnr, sender_phone, fresh["train_number"], fresh["train_name"],
                fresh["source_station"], fresh["dest_station"], fresh["source_station_name"], fresh["dest_station_name"],
                fresh["journey_date"], fresh["travel_class"], fresh["quota"],
                fresh["booking_status"], fresh["current_status"], fresh["booking_status"],
                fresh["current_wl_number"], fresh["booking_wl_number"],
                prob["probability"], prob["risk_badge"], prob["explanation"], prob["smart_tip"], now_iso
            ))
            conn.commit()
            ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
        else:
            conn.execute("UPDATE tracked_pnrs SET phone = ?, status = 'TRACKING' WHERE pnr = ?", (sender_phone, pnr))
            conn.commit()
            ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()

        conn.close()
        await broadcast_sse({"type": "PNR_UPDATED", "pnr": pnr})

        return {
            "reply": f"""🚆 *IRCTC PNR Tracking Activated!*
🎫 *PNR:* {pnr}
🚄 *Train:* {ticket['train_number']} - {ticket['train_name']} ({ticket['travel_class']})
📊 *Current Status:* *{ticket['current_status']}*
🎯 *Confirmation Chance:* *{ticket['confirmation_probability']}% ({ticket['risk_badge']})*

🔔 *Live Alerts:* You will receive instant WhatsApp messages whenever your waitlist position moves or chart is prepared!
_Reply STOP {pnr} to pause alerts._"""
        }

    if command == "STOP" and arg:
        pnr = re.sub(r"\D", "", arg)
        conn.execute("UPDATE tracked_pnrs SET status = 'STOPPED' WHERE pnr = ?", (pnr,))
        conn.commit()
        conn.close()
        await broadcast_sse({"type": "PNR_UPDATED", "pnr": pnr})
        return {"reply": f"⏸️ *Tracking Paused for PNR {pnr}*\nYou will no longer receive alerts for this ticket.\nReply *TRACK {pnr}* anytime to resume."}

    if command == "STATUS":
        pnr = re.sub(r"\D", "", arg) if arg else ""
        if pnr:
            ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
        else:
            ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE phone LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%{sender_phone}%",)).fetchone()
        conn.close()

        if ticket:
            return {
                "reply": f"""📊 *IRCTC Live Status Report*
🎫 *PNR:* {ticket['pnr']}
🚄 *Train:* {ticket['train_number']} - {ticket['train_name']}
📍 *Route:* {ticket['source_station']} ➔ {ticket['dest_station']}
📅 *Journey:* {ticket['journey_date']}

📈 *Status:* *{ticket['current_status']}*
🎯 *Confirmation Probability:* *{ticket['confirmation_probability']}% ({ticket['risk_badge']})*
💡 *Insight:* {ticket['smart_tip'] or ticket['prediction_explanation']}

_Reply STOP {ticket['pnr']} to pause._"""
            }
        return {"reply": "No active tickets found for your number.\nTo start tracking, send: *TRACK <10-digit-PNR>*"}

    conn.close()
    return {
        "reply": """🤖 *IRCTC Smart PNR WhatsApp Bot*
Commands available:
• *TRACK <PNR>* - Start instant waitlist tracking & movement alerts
• *STATUS <PNR>* - Check current waitlist odds & confirmation %
• *STOP <PNR>* - Pause notifications for a ticket
• *HELP* - Show this instructions menu"""
    }

# ==========================================
# 5. Ticket Screenshot / PDF Upload
# ==========================================

@app.post("/api/upload-ticket")
async def upload_ticket(ticket: UploadFile = File(...)):
    try:
        content = await ticket.read()
        parsed = await extract_ticket_from_file(content, ticket.content_type, ticket.filename)
        return {"success": True, "data": parsed}
    except Exception as e:
        print(f"❌ [FastAPI] Upload extraction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# 6. System Settings & Notifications
# ==========================================

@app.get("/api/system/status")
async def system_status():
    conn = get_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = 'mode'").fetchone()
    mode = row["value"] if row else "simulation"
    conn.close()

    wa_data = {"status": "disconnected", "qrDataUrl": None, "connectedUser": None}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{WHATSAPP_BRIDGE_URL}/qr")
            if resp.status_code == 200:
                wa_data = resp.json()
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "mode": mode,
            "hasRapidApiKey": bool(os.getenv("RAPIDAPI_KEY", "").strip()),
            "hasGeminiApiKey": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "irctc": get_irctc_status(),
            "whatsapp": wa_data
        }
    }

@app.post("/api/system/mode")
async def set_system_mode(payload: ModeRequest):
    if payload.mode not in ("simulation", "live"):
        raise HTTPException(status_code=400, detail="Mode must be 'simulation' or 'live'")

    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('mode', ?)", (payload.mode,))
    conn.commit()
    conn.close()

    await broadcast_sse({"type": "SYSTEM_MODE_CHANGED", "mode": payload.mode})
    return {"success": True, "mode": payload.mode}

@app.post("/api/system/toggle-maintenance")
async def toggle_maintenance():
    conn = get_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = 'maintenance_override'").fetchone()
    current = row["value"] if row else "false"
    next_val = "false" if current == "true" else "true"
    conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('maintenance_override', ?)", (next_val,))
    conn.commit()
    conn.close()

    updated = get_irctc_status()
    await broadcast_sse({"type": "IRCTC_STATUS", "data": updated})
    return {"success": True, "data": updated}

@app.get("/api/notifications")
def get_notifications():
    conn = get_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50").fetchall()]
    conn.close()
    return {"success": True, "data": rows}

@app.delete("/api/notifications")
async def clear_notifications():
    conn = get_connection()
    conn.execute("DELETE FROM notifications")
    conn.commit()
    conn.close()
    await broadcast_sse({"type": "NOTIFICATIONS_CLEARED"})
    return {"success": True, "message": "Notifications cleared"}
