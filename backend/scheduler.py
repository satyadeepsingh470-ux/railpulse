import asyncio
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_connection
from predictor import calculate_probability
from pnr_simulator import fetch_live_or_simulated_pnr, send_whatsapp_alert

scheduler = AsyncIOScheduler()
last_poll_time = None

def get_irctc_status():
    # Calculate IST time (UTC + 5:30)
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    current_mins = ist_now.hour * 60 + ist_now.minute

    conn = get_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = 'maintenance_override'").fetchone()
    is_forced = (row["value"] == "true") if row else False
    conn.close()

    # 23:45 is 1425 mins, 00:30 is 30 mins
    is_maintenance_time = (current_mins >= 1425) or (current_mins < 30)
    in_maintenance = is_forced or is_maintenance_time

    formatted_ist = ist_now.strftime("%I:%M:%S %p IST")

    return {
        "inMaintenance": in_maintenance,
        "isForced": is_forced,
        "istTime": formatted_ist,
        "rawIst": ist_now.isoformat(),
        "statusLabel": "IRCTC Night Maintenance Active" if in_maintenance else "IRCTC Servers Normal & Operational",
        "windowInfo": "11:45 PM – 12:30 AM IST Daily Maintenance Window"
    }

async def poll_active_pnrs(sse_broadcast=None):
    global last_poll_time
    irctc = get_irctc_status()
    now_iso = datetime.utcnow().isoformat()
    last_poll_time = now_iso

    if irctc["inMaintenance"]:
        print(f"🌙 [APScheduler] Skipping check at {irctc['istTime']}: IRCTC Night Maintenance Window active (23:45 - 00:30 IST).")
        if sse_broadcast:
            await sse_broadcast({
                "type": "CRON_STATUS",
                "data": {"lastPoll": now_iso, "status": "PAUSED_MAINTENANCE", "message": "Auto-poll paused during IRCTC Maintenance."}
            })
        return {"skipped": True, "reason": "MAINTENANCE_WINDOW"}

    conn = get_connection()
    active_tickets = conn.execute("SELECT * FROM tracked_pnrs WHERE status = 'TRACKING'").fetchall()
    print(f"🔍 [APScheduler] Checking {len(active_tickets)} active PNRs at {irctc['istTime']}...")

    updated_count = 0

    for row in active_tickets:
        ticket = dict(row)
        pnr = ticket["pnr"]

        try:
            fresh = await fetch_live_or_simulated_pnr(pnr)
            prev_status = ticket["current_status"]
            new_status = fresh["current_status"]
            chart_flipped = (fresh["chart_prepared"] == 1 and ticket["chart_prepared"] == 0)

            # Strict State Diffing
            if prev_status == new_status and not chart_flipped:
                conn.execute("UPDATE tracked_pnrs SET last_checked_at = ? WHERE pnr = ?", (now_iso, pnr))
                continue

            print(f"⚡ [Diff Engine] Movement detected for PNR {pnr}: '{prev_status}' ➔ '{new_status}'")
            updated_count += 1

            new_wl = fresh.get("current_wl_number", 0)
            prev_wl = ticket.get("current_wl_number", 0)
            cleared = max(0, prev_wl - new_wl)

            prob = calculate_probability(
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

            conn.execute("""
                UPDATE tracked_pnrs SET
                    previous_status = ?,
                    current_status = ?,
                    current_wl_number = ?,
                    chart_prepared = ?,
                    confirmation_probability = ?,
                    risk_badge = ?,
                    prediction_explanation = ?,
                    smart_tip = ?,
                    last_checked_at = ?
                WHERE pnr = ?
            """, (
                prev_status, new_status, new_wl, fresh["chart_prepared"],
                prob["probability"], prob["risk_badge"], prob["explanation"],
                prob["smart_tip"], now_iso, pnr
            ))

            note = f"Waitlist moved up by {cleared} berths" if cleared > 0 else ("Chart Prepared" if chart_flipped else "Status updated")
            conn.execute("""
                INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pnr, new_status, new_wl, prob["probability"], note, now_iso))

            conn.commit()

            movement_snippet = f"(Moved up by {cleared}!)" if cleared > 0 else ""
            alert_text = f"""🚆 *IRCTC Waitlist Movement Alert!*
🎫 *PNR:* {pnr}
🚄 *Train:* {ticket['train_number']} - {ticket['train_name']} ({ticket['travel_class']})

📉 *Previous Status:* {prev_status}
📈 *Current Status:* *{new_status}* {movement_snippet}
🎯 *Confirmation Chance:* *{prob['probability']}% ({prob['risk_badge']})*

⏳ *Next auto-check in:* 2 hours
_Reply STOP {pnr} to mute alerts._"""

            notif = await send_whatsapp_alert(ticket["phone"], alert_text, pnr, "MOVEMENT")

            if sse_broadcast:
                await sse_broadcast({"type": "PNR_UPDATED", "pnr": pnr})
                await sse_broadcast({"type": "NEW_NOTIFICATION", "data": notif})

        except Exception as e:
            print(f"Error checking PNR {pnr}: {e}")

    conn.commit()
    conn.close()

    return {"checked": len(active_tickets), "updated": updated_count}

def start_scheduler(loop, sse_broadcast):
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(poll_active_pnrs(sse_broadcast), loop),
        "interval",
        minutes=5,
        id="pnr_poller"
    )
    scheduler.start()
    print("⏰ [APScheduler] Poller scheduled every 5 minutes.")
