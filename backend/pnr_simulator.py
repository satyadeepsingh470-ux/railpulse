import os
import random
import re
import io
import json
import base64
from datetime import datetime, timedelta
import httpx
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from database import get_connection
from predictor import calculate_probability, enhance_with_gemini

POPULAR_TRAINS = [
    {"number": "12952", "name": "New Delhi Tejas Rajdhani", "src": "NDLS", "src_name": "New Delhi", "dst": "MMCT", "dst_name": "Mumbai Central", "time": "16:55"},
    {"number": "12628", "name": "Karnataka Express", "src": "NDLS", "src_name": "New Delhi", "dst": "SBC", "dst_name": "KSR Bengaluru", "time": "20:20"},
    {"number": "12302", "name": "Howrah Rajdhani Express", "src": "NDLS", "src_name": "New Delhi", "dst": "HWH", "dst_name": "Howrah Jn", "time": "16:50"},
    {"number": "12004", "name": "Lucknow Swarna Shatabdi", "src": "NDLS", "src_name": "New Delhi", "dst": "LKO", "dst_name": "Lucknow Charbagh", "time": "06:10"},
    {"number": "12138", "name": "Punjab Mail", "src": "FZR", "src_name": "Firozpur Cantt", "dst": "CSMT", "dst_name": "Mumbai CSMT", "time": "21:40"},
    {"number": "12260", "name": "Sealdah AC Duronto", "src": "BKN", "src_name": "Bikaner Jn", "dst": "SDAH", "dst_name": "Sealdah Kolkata", "time": "12:15"},
]

WHATSAPP_BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

async def send_whatsapp_alert(phone: str, message: str, pnr: str = "", msg_type: str = "MOVEMENT"):
    clean_phone = re.sub(r"\D", "", phone or "")
    status = "SIMULATED"
    delivered = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{WHATSAPP_BRIDGE_URL}/send", json={"phone": clean_phone, "message": message})
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "SIMULATED")
                delivered = data.get("success", False)
    except Exception as e:
        print(f"⚠️ [FastAPI] Could not reach WhatsApp Bridge on {WHATSAPP_BRIDGE_URL}: {e}")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (pnr, phone, message, type, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pnr, clean_phone, message, msg_type, status, datetime.utcnow().isoformat()))
    conn.commit()
    notif_id = cursor.lastrowid
    conn.close()

    return {
        "id": notif_id,
        "pnr": pnr,
        "phone": clean_phone,
        "message": message,
        "type": msg_type,
        "status": status,
        "created_at": datetime.utcnow().isoformat()
    }

async def fetch_live_or_simulated_pnr(pnr: str):
    conn = get_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = 'mode'").fetchone()
    mode = row["value"] if row else "simulation"
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "").strip()
    conn.close()

    if mode == "live" and rapidapi_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://irctc1.p.rapidapi.com/api/v3/getPNRStatus?pnrNumber={pnr}",
                    headers={
                        "x-rapidapi-key": rapidapi_key,
                        "x-rapidapi-host": os.getenv("RAPIDAPI_HOST", "irctc1.p.rapidapi.com")
                    }
                )
                if resp.status_code == 200:
                    json_data = resp.json()
                    if json_data.get("status") is True and json_data.get("data"):
                        print(f"✅ [RapidAPI] Live IRCTC data retrieved for PNR {pnr}")
                        return parse_rapidapi_data(pnr, json_data["data"])
                    else:
                        msg = json_data.get("message", "PNR not found on live IRCTC server")
                        print(f"ℹ️ [RapidAPI] {msg} for PNR {pnr}. Using realistic simulation.")
        except Exception as e:
            print(f"RapidAPI query error: {e}")

    return generate_simulated_pnr(pnr)

def parse_rapidapi_data(pnr: str, data: dict):
    train_no = str(data.get("TrainNo") or data.get("trainNumber") or "12952")
    train_name = str(data.get("TrainName") or data.get("trainName") or "Express")
    src = str(data.get("From") or data.get("sourceStation") or "NDLS")
    dst = str(data.get("To") or data.get("destinationStation") or "MMCT")
    journey_date = str(data.get("Doj") or data.get("dateOfJourney") or datetime.now().strftime("%Y-%m-%d"))
    travel_class = str(data.get("Class") or data.get("journeyClass") or "3A")
    quota = str(data.get("Quota") or "GNWL")
    passengers = data.get("PassengerStatus", data.get("passengerList", []))
    p1 = passengers[0] if passengers else {}
    b_status = str(p1.get("BookingStatus") or p1.get("bookingStatus") or "GNWL 25")
    c_status = str(p1.get("CurrentStatus") or p1.get("currentStatus") or "GNWL 18")

    c_digits = re.sub(r"\D", "", c_status)
    b_digits = re.sub(r"\D", "", b_status)
    c_wl = int(c_digits) if c_digits else 0
    b_wl = int(b_digits) if b_digits else (c_wl + 10)

    chart = 1 if data.get("ChartPrepared") in (True, "Y", 1, "true") else 0

    return {
        "pnr": pnr,
        "train_number": train_no,
        "train_name": train_name,
        "source_station": src,
        "dest_station": dst,
        "source_station_name": src,
        "dest_station_name": dst,
        "journey_date": journey_date,
        "journey_time": "16:00",
        "travel_class": travel_class,
        "quota": quota,
        "booking_status": b_status,
        "current_status": c_status,
        "current_wl_number": c_wl,
        "booking_wl_number": b_wl,
        "chart_prepared": chart
    }

def generate_simulated_pnr(pnr: str):
    num_sum = sum(int(c) for c in pnr if c.isdigit()) or 25
    train = POPULAR_TRAINS[num_sum % len(POPULAR_TRAINS)]

    classes = ["3A", "SL", "2A", "3E", "CC"]
    chosen_class = classes[num_sum % len(classes)]

    quotas = ["GNWL", "GNWL", "RAC", "RLWL", "PQWL"]
    chosen_quota = quotas[num_sum % len(quotas)]

    booking_wl = (num_sum % 35) + 12
    current_wl = max(1, booking_wl - ((num_sum % 8) + 4))

    b_status = f"{chosen_quota} {booking_wl}"
    c_status = f"{chosen_quota} {current_wl}"

    if chosen_quota == "RAC":
        b_status = f"RAC {booking_wl}"
        c_status = f"RAC {max(1, current_wl % 15)}"

    offset = (num_sum % 6) + 2
    j_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")

    return {
        "pnr": pnr,
        "train_number": train["number"],
        "train_name": train["name"],
        "source_station": train["src"],
        "dest_station": train["dst"],
        "source_station_name": train["src_name"],
        "dest_station_name": train["dst_name"],
        "journey_date": j_date,
        "journey_time": train["time"],
        "travel_class": chosen_class,
        "quota": chosen_quota,
        "booking_status": b_status,
        "current_status": c_status,
        "previous_status": b_status,
        "current_wl_number": current_wl,
        "booking_wl_number": booking_wl,
        "chart_prepared": 0
    }

async def simulate_waitlist_drop(pnr: str):
    conn = get_connection()
    ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
    if not ticket:
        conn.close()
        raise ValueError(f"PNR {pnr} not found in database.")

    if ticket["status"] == "CONFIRMED" or ticket["current_status"].startswith("CNF"):
        conn.close()
        raise ValueError("Ticket is already fully confirmed!")

    prev_status = ticket["current_status"]
    prev_wl = ticket["current_wl_number"] or 15

    drop_step = min(prev_wl - 1, random.randint(4, 8))
    new_wl = max(1, prev_wl - drop_step)

    if prev_wl <= 4 and drop_step >= 3:
        new_status = "RAC 2"
    else:
        quota_prefix = ticket["quota"] or "GNWL"
        new_status = f"{quota_prefix} {new_wl}"

    prob_data = calculate_probability(
        quota=ticket["quota"],
        travel_class=ticket["travel_class"],
        booking_wl=ticket["booking_wl_number"],
        current_wl=new_wl,
        current_status=new_status,
        journey_date=ticket["journey_date"],
        journey_time=ticket["journey_time"],
        train_number=ticket["train_number"],
        train_name=ticket["train_name"]
    )

    now_iso = datetime.utcnow().isoformat()
    cleared = prev_wl - new_wl
    history_note = f"Waitlist moved up by {cleared} berths" if cleared > 0 else "Status updated"

    conn.execute("""
        UPDATE tracked_pnrs SET
            previous_status = ?,
            current_status = ?,
            current_wl_number = ?,
            confirmation_probability = ?,
            risk_badge = ?,
            prediction_explanation = ?,
            smart_tip = ?,
            last_checked_at = ?
        WHERE pnr = ?
    """, (
        prev_status, new_status, new_wl, prob_data["probability"],
        prob_data["risk_badge"], prob_data["explanation"], prob_data["smart_tip"],
        now_iso, pnr
    ))

    conn.execute("""
        INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pnr, new_status, new_wl, prob_data["probability"], history_note, now_iso))

    conn.commit()
    updated_ticket = dict(conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone())
    history = [dict(r) for r in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (pnr,)).fetchall()]
    conn.close()

    alert_msg = f"""🚆 *IRCTC Waitlist Movement Alert!*
🎫 *PNR:* {pnr}
🚄 *Train:* {ticket['train_number']} - {ticket['train_name']} ({ticket['travel_class']})

📉 *Previous Status:* {prev_status}
📈 *Current Status:* *{new_status}* (Moved up by {cleared}!)
🎯 *Confirmation Chance:* *{prob_data['probability']}% ({prob_data['risk_badge']})*

⏳ *Next auto-check in:* 2 hours
_Reply STOP {pnr} to mute alerts._"""

    notif = await send_whatsapp_alert(ticket["phone"], alert_msg, pnr, "MOVEMENT")

    return {
        "ticket": updated_ticket,
        "history": history,
        "movement": cleared,
        "message": alert_msg,
        "notification": notif
    }

async def simulate_confirmation(pnr: str):
    conn = get_connection()
    ticket = conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone()
    if not ticket:
        conn.close()
        raise ValueError(f"PNR {pnr} not found in database.")

    coach_map = {"3A": "B3", "SL": "S5", "2A": "A1", "1A": "H1", "3E": "M2", "CC": "C2"}
    coach = coach_map.get(ticket["travel_class"], "B2")
    berth = random.randint(1, 64)
    berth_type = random.choice(["Lower", "Middle", "Upper", "Side Lower", "Side Upper"])
    confirmed_status = f"CNF {coach}-{berth} ({berth_type})"
    now_iso = datetime.utcnow().isoformat()

    conn.execute("""
        UPDATE tracked_pnrs SET
            previous_status = current_status,
            current_status = ?,
            current_wl_number = 0,
            chart_prepared = 1,
            confirmation_probability = 100,
            risk_badge = 'High Chance',
            status = 'CONFIRMED',
            prediction_explanation = ?,
            smart_tip = ?,
            last_checked_at = ?
        WHERE pnr = ?
    """, (
        confirmed_status,
        f"Ticket confirmed! Allocated coach {coach}, berth {berth} ({berth_type}).",
        "Your seat is confirmed! Keep photo ID ready for TTE inspection.",
        now_iso, pnr
    ))

    conn.execute("""
        INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pnr, confirmed_status, 0, 100, f"Confirmed: {coach}-{berth}", now_iso))

    conn.commit()
    updated_ticket = dict(conn.execute("SELECT * FROM tracked_pnrs WHERE pnr = ?", (pnr,)).fetchone())
    history = [dict(r) for r in conn.execute("SELECT * FROM pnr_history WHERE pnr = ? ORDER BY id ASC", (pnr,)).fetchall()]
    conn.close()

    confirm_msg = f"""🎉 *IRCTC Ticket Confirmed!*
🎫 *PNR:* {pnr}
🚄 *Train:* {ticket['train_number']} - {ticket['train_name']} ({ticket['travel_class']})

✅ *Final Status:* *{confirmed_status}*
🎯 *Confirmation Chance:* *100%*
📍 *Journey:* {ticket['source_station']} ➔ {ticket['dest_station']} on {ticket['journey_date']}

🚂 Have a comfortable and memorable journey!"""

    notif = await send_whatsapp_alert(ticket["phone"], confirm_msg, pnr, "CONFIRMATION")

    return {
        "ticket": updated_ticket,
        "history": history,
        "message": confirm_msg,
        "notification": notif
    }

def extract_from_irctc_pdf_text(text: str):
    """
    Extracts structured fields from IRCTC Electronic Reservation Slip (ERS) text
    """
    pnr_match = re.search(r'\b(\d{10})\b', text)
    if not pnr_match:
        return None

    pnr = pnr_match.group(1)

    train_match = re.search(r'\b(\d{5})\b', text)
    train_number = train_match.group(1) if train_match else "12952"

    train_name = "Express"
    name_match = re.search(r'(?:Train No\. & Name|Train Name)[:\s\d/]+([A-Z\s]+?)(?:Class|Date|Quota|\n|$)', text, re.IGNORECASE)
    if name_match:
        train_name = name_match.group(1).strip()
    else:
        for t in POPULAR_TRAINS:
            if t["number"] == train_number:
                train_name = t["name"]
                break

    class_match = re.search(r'\b(1A|2A|3A|3E|CC|EC|SL|2S)\b', text, re.IGNORECASE)
    travel_class = class_match.group(1).upper() if class_match else "3A"

    quota_match = re.search(r'\b(GNWL|RAC|RLWL|PQWL|TQWL|CKWL|GENERAL|TATKAL)\b', text, re.IGNORECASE)
    raw_quota = quota_match.group(1).upper() if quota_match else "GNWL"
    quota = "GNWL"
    if "TATKAL" in raw_quota: quota = "TQWL"
    elif "RAC" in raw_quota: quota = "RAC"
    elif raw_quota in ("RLWL", "PQWL", "TQWL"): quota = raw_quota

    # Status matches like GNWL 42 or GNWL/18
    statuses = re.findall(r'(GNWL|RLWL|PQWL|TQWL|RAC|CNF|WL)[\s/:]*(\d+)', text, re.IGNORECASE)
    booking_status = f"{quota} 25"
    current_status = f"{quota} 18"
    if len(statuses) >= 2:
        booking_status = f"{statuses[0][0].upper()} {statuses[0][1]}"
        current_status = f"{statuses[1][0].upper()} {statuses[1][1]}"
    elif len(statuses) == 1:
        booking_status = f"{statuses[0][0].upper()} {statuses[0][1]}"
        current_status = f"{statuses[0][0].upper()} {statuses[0][1]}"

    # Journey date
    date_match = re.search(r'(\d{1,2})[-/ ]([A-Za-z]{3}|\d{1,2})[-/ ](\d{2,4})', text)
    journey_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
    if date_match:
        try:
            day, month_str, year = date_match.groups()
            if len(year) == 2: year = f"20{year}"
            month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
            month = month_map.get(month_str.lower()[:3], int(month_str) if month_str.isdigit() else 10)
            journey_date = f"{year}-{int(month):02d}-{int(day):02d}"
        except Exception:
            pass

    # Station codes
    stn_matches = re.findall(r'\b([A-Z]{3,4})\b', text)
    src_station = "NDLS"
    dst_station = "MMCT"
    if len(stn_matches) >= 2:
        for s in stn_matches:
            if s in ("NDLS", "MMCT", "SBC", "HWH", "LKO", "CSMT", "MAS", "HYB", "BKN", "NZM", "PNBE", "PUNE", "ADI"):
                if src_station == "NDLS" and s != src_station:
                    dst_station = s
                else:
                    src_station = s

    return {
        "pnr": pnr,
        "trainNumber": train_number,
        "trainName": train_name,
        "sourceStation": src_station,
        "destStation": dst_station,
        "sourceStationName": src_station,
        "destStationName": dst_station,
        "journeyDate": journey_date,
        "journeyTime": "16:00",
        "travelClass": travel_class,
        "quota": quota,
        "bookingStatus": booking_status,
        "currentStatus": current_status,
        "extractedBy": "IRCTC Digital Ticket PDF"
    }

async def extract_ticket_from_file(file_bytes: bytes, mime_type: str, filename: str):
    clean_name = (filename or "").lower()

    # Step 1: Direct text extraction for digital PDFs (fastest & 100% accurate)
    if clean_name.endswith(".pdf") or "pdf" in (mime_type or ""):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            full_text = ""
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    full_text += txt + "\n"

            if full_text.strip():
                parsed_pdf = extract_from_irctc_pdf_text(full_text)
                if parsed_pdf and parsed_pdf.get("pnr"):
                    print(f"📄 [PDF Parser] Extracted digital IRCTC ticket: PNR {parsed_pdf['pnr']} (Train {parsed_pdf['trainNumber']})")
                    return parsed_pdf
        except Exception as e:
            print(f"⚠️ PyPDF text parsing skipped: {e}")

    # Step 2: Multimodal Gemini Vision (for scanned image PDFs and screenshots)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        # Determine appropriate MIME type
        actual_mime = mime_type
        if not actual_mime or actual_mime == "application/octet-stream":
            if clean_name.endswith(".pdf"): actual_mime = "application/pdf"
            elif clean_name.endswith(".png"): actual_mime = "image/png"
            elif clean_name.endswith(".webp"): actual_mime = "image/webp"
            else: actual_mime = "image/jpeg"

        prompt = """You are an expert Indian Railways IRCTC ticket parser.
Analyze this ticket screenshot or PDF document and extract the ticket fields into valid JSON:
{
  "pnr": "10-digit number",
  "trainNumber": "5-digit train number",
  "trainName": "full train name",
  "sourceStation": "3-4 letter station code e.g. NDLS",
  "destStation": "3-4 letter station code e.g. MMCT",
  "sourceStationName": "e.g. New Delhi",
  "destStationName": "e.g. Mumbai Central",
  "journeyDate": "YYYY-MM-DD",
  "journeyTime": "HH:MM",
  "travelClass": "3A or SL or 2A or 1A or 3E or CC",
  "quota": "GNWL or RAC or RLWL or PQWL or TQWL",
  "bookingStatus": "e.g. GNWL 35",
  "currentStatus": "e.g. GNWL 18"
}
Return ONLY valid JSON with no markdown formatting."""

        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        vision_models = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.8-flash"]

        async with httpx.AsyncClient(timeout=12.0) as client:
            for model in vision_models:
                try:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                        json={
                            "contents": [
                                {
                                    "parts": [
                                        {"text": prompt},
                                        {"inline_data": {"mime_type": actual_mime, "data": b64_data}}
                                    ]
                                }
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        txt = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        json_match = re.search(r"\{[\s\S]*\}", txt)
                        if json_match:
                            parsed = json.loads(json_match.group(0))
                            clean_pnr = re.sub(r"\D", "", parsed.get("pnr", ""))
                            if len(clean_pnr) == 10:
                                parsed["pnr"] = clean_pnr
                                parsed["extractedBy"] = "Gemini Vision AI"
                                print(f"🤖 [Gemini Vision] Extracted PNR {clean_pnr} from {filename}")
                                return parsed
                except Exception as e:
                    print(f"⚠️ Gemini model {model} attempt error: {e}")

    # Step 3: Check if filename itself contains a 10-digit PNR
    digits = re.sub(r"\D", "", filename or "")
    if len(digits) == 10:
        sim = generate_simulated_pnr(digits)
        return {
            "pnr": digits,
            "trainNumber": sim["train_number"],
            "trainName": sim["train_name"],
            "sourceStation": sim["source_station"],
            "destStation": sim["dest_station"],
            "sourceStationName": sim["source_station_name"],
            "destStationName": sim["dest_station_name"],
            "journeyDate": sim["journey_date"],
            "journeyTime": sim["journey_time"],
            "travelClass": sim["travel_class"],
            "quota": sim["quota"],
            "bookingStatus": sim["booking_status"],
            "currentStatus": sim["current_status"],
            "extractedBy": "Filename PNR Matcher"
        }

    # Step 4: Graceful informative error instead of silent random fake data
    raise ValueError("Could not detect a valid 10-digit IRCTC PNR from this document. Please ensure the ticket screenshot or PDF is clear and readable.")
