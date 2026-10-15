import os
import re
from datetime import datetime
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

QUOTA_CONFIG = {
    "GNWL": {"multiplier": 1.25, "base_bonus": 15, "name": "General Waiting List"},
    "RAC": {"multiplier": 1.50, "base_bonus": 45, "name": "Reservation Against Cancellation"},
    "RLWL": {"multiplier": 0.85, "base_bonus": -10, "name": "Remote Location Waiting List"},
    "PQWL": {"multiplier": 0.65, "base_bonus": -25, "name": "Pooled Quota Waiting List"},
    "RSWL": {"multiplier": 0.70, "base_bonus": -20, "name": "Road-side Waiting List"},
    "TQWL": {"multiplier": 0.35, "base_bonus": -40, "name": "Tatkal Waiting List"},
    "CKWL": {"multiplier": 0.35, "base_bonus": -40, "name": "Tatkal Waiting List"},
}

CLASS_CONFIG = {
    "SL": {"factor": 1.25, "coaches": "10-14 coaches", "turnover": "very high"},
    "3A": {"factor": 1.15, "coaches": "6-11 coaches", "turnover": "high"},
    "3E": {"factor": 1.10, "coaches": "4-6 coaches", "turnover": "high"},
    "2A": {"factor": 0.80, "coaches": "2-4 coaches", "turnover": "moderate"},
    "1A": {"factor": 0.45, "coaches": "1-2 coaches", "turnover": "low"},
    "CC": {"factor": 1.05, "coaches": "6-10 coaches", "turnover": "moderate"},
    "EC": {"factor": 0.50, "coaches": "1-2 coaches", "turnover": "low"},
    "2S": {"factor": 1.15, "coaches": "4-8 coaches", "turnover": "high"},
}

def calculate_probability(
    quota: str = "GNWL",
    travel_class: str = "3A",
    booking_wl: int = 30,
    current_wl: int = 15,
    current_status: str = "",
    journey_date: str = "",
    journey_time: str = "16:00",
    train_number: str = "",
    train_name: str = ""
):
    norm_status = (current_status or "").upper().strip()

    # Confirmed
    if norm_status.startswith("CNF") or "CONFIRM" in norm_status:
        return {
            "probability": 100,
            "risk_badge": "High Chance",
            "badge_color": "emerald",
            "explanation": "Berth confirmed. Coach and seat details allocated.",
            "smart_tip": "Ticket is confirmed! Keep a digital copy and valid photo ID handy during your journey."
        }

    # RAC (Reservation Against Cancellation)
    if norm_status.startswith("RAC") or quota.upper() == "RAC":
        rac_digits = re.sub(r"\D", "", norm_status)
        rac_num = int(rac_digits) if rac_digits else (current_wl or 1)
        prob = min(99, max(90, 99 - int(rac_num * 0.5)))
        return {
            "probability": prob,
            "risk_badge": "High Chance",
            "badge_color": "emerald",
            "explanation": f"RAC status guarantees boarding and a shared berth. {prob}% probability of upgrading to a full confirmed berth.",
            "smart_tip": "RAC passengers are guaranteed boarding rights. Final berth allocations are finalized during chart preparation."
        }

    clean_quota = quota.upper().strip()
    quota_data = QUOTA_CONFIG.get(clean_quota, QUOTA_CONFIG["GNWL"])
    class_data = CLASS_CONFIG.get(travel_class.upper(), CLASS_CONFIG["3A"])

    initial_wl = max(1, int(booking_wl or current_wl or 1))
    active_wl = max(1, int(current_wl or initial_wl))

    # Calculate hours to departure
    hours_remaining = 72
    if journey_date:
        try:
            dep_dt = datetime.fromisoformat(f"{journey_date}T{journey_time or '12:00'}:00")
            diff = dep_dt - datetime.now()
            hours_remaining = max(1, int(diff.total_seconds() / 3600))
        except Exception:
            hours_remaining = 72

    # 1. Base score from current Waitlist number
    if active_wl <= 5:
        base_score = 88
    elif active_wl <= 12:
        base_score = 78
    elif active_wl <= 20:
        base_score = 68
    elif active_wl <= 35:
        base_score = 55
    elif active_wl <= 50:
        base_score = 42
    elif active_wl <= 80:
        base_score = 30
    else:
        base_score = 18

    # 2. Movement Velocity Factor
    positions_cleared = max(0, initial_wl - active_wl)
    clearance_rate = (positions_cleared / initial_wl) if initial_wl > 0 else 0
    velocity_bonus = min(22, round(clearance_rate * 25))

    # 3. Time Remaining Decay / Boost
    if hours_remaining > 168:
        time_factor = 1.05
    elif 24 <= hours_remaining <= 168:
        time_factor = 1.10
    elif 4 <= hours_remaining < 24:
        time_factor = 1.15 if active_wl <= 15 else 0.85
    else:
        time_factor = 1.0 if active_wl <= 5 else 0.60

    # 4. Composite score
    raw_score = (base_score + quota_data["base_bonus"] + velocity_bonus) * quota_data["multiplier"] * class_data["factor"] * time_factor
    if positions_cleared >= 10:
        raw_score += 6

    probability = round(raw_score)
    if clean_quota in ("TQWL", "CKWL"):
        probability = min(probability, 65 if active_wl <= 3 else 25)
    elif clean_quota == "PQWL":
        probability = min(probability, 68 if active_wl <= 10 else 35)

    probability = max(5, min(98, probability))

    # Risk badge
    if probability >= 75:
        risk_badge = "High Chance"
        badge_color = "emerald"
    elif probability < 45:
        risk_badge = "High Risk"
        badge_color = "rose"
    else:
        risk_badge = "Moderate"
        badge_color = "amber"

    # Human explanation
    if clean_quota == "GNWL":
        explanation = f"GNWL on {travel_class} ({class_data['coaches']}) has {class_data['turnover']} cancellation turnover. Cleared {positions_cleared} berths so far."
    elif clean_quota == "RLWL":
        explanation = f"RLWL on {travel_class} moves moderately. Remote location quota is allocated with {positions_cleared} cleared berths."
    elif clean_quota == "PQWL":
        explanation = f"PQWL has a restricted intermediate station quota pool. Movement is historically lower than General quota."
    elif clean_quota in ("TQWL", "CKWL"):
        explanation = "Tatkal Waitlist (TQWL) rarely clears because Tatkal cancellations yield zero refund."
    else:
        explanation = f"{clean_quota} quota on {travel_class} with {hours_remaining} hrs to departure."

    smart_tip = generate_heuristic_tip(travel_class, clean_quota, probability)

    return {
        "probability": probability,
        "risk_badge": risk_badge,
        "badge_color": badge_color,
        "explanation": explanation,
        "smart_tip": smart_tip,
        "hours_remaining": hours_remaining
    }

def generate_heuristic_tip(travel_class: str, quota: str, probability: int) -> str:
    if probability >= 80:
        return f"{travel_class} coach composition on this route typically experiences 15-20 cancellations post-Tatkal opening. High odds of confirmed berth."
    if probability >= 60:
        return "Chart prepares ~4 hours before departure. Headquarter (HO) and Emergency Quota release at charting usually clears single-digit waitlists."
    if quota == "PQWL":
        return "PQWL tickets have low movement. Consider checking alternate trains or Tatkal booking opening at 10 AM (AC) / 11 AM (Non-AC) 1 day prior."
    if quota in ("TQWL", "CKWL"):
        return "TQWL rarely converts to CNF due to non-refundable Tatkal cancellation policy. Have an alternate travel backup ready."
    return "Keep monitoring status. If chart prepares and status remains WL, e-tickets are automatically cancelled and refunded to source account."

async def enhance_with_gemini(
    train_number: str,
    train_name: str,
    travel_class: str,
    quota: str,
    current_status: str,
    current_wl: int,
    probability: int,
    risk_badge: str
) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return ""

    try:
        prompt = f"""You are an IRCTC Indian Railways ticketing intelligence expert.
Given ticket details:
- Train: {train_number} {train_name}
- Class: {travel_class}, Quota: {quota}
- Current Status: {current_status} (WL: {current_wl})
- Calculated Confirmation Chance: {probability}% ({risk_badge})

Write exactly ONE concise, highly actionable sentence (max 25 words) with practical advice or historical insight (e.g., chart prep timing, Tatkal backup, RAC probability, or cancellation trends). Do not include disclaimers."""

        async with httpx.AsyncClient(timeout=4.0) as client:
            for model in ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.8-flash"]:
                try:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 60}
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        if text:
                            return text
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Gemini tip generation skipped: {e}")

    return ""
