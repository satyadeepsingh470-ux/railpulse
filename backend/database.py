import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "pnr_tracker.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS tracked_pnrs (
        pnr TEXT PRIMARY KEY,
        phone TEXT NOT NULL,
        train_number TEXT NOT NULL,
        train_name TEXT NOT NULL,
        source_station TEXT NOT NULL,
        dest_station TEXT NOT NULL,
        source_station_name TEXT,
        dest_station_name TEXT,
        journey_date TEXT NOT NULL,
        journey_time TEXT DEFAULT '16:00',
        travel_class TEXT NOT NULL,
        quota TEXT NOT NULL,
        booking_status TEXT NOT NULL,
        current_status TEXT NOT NULL,
        previous_status TEXT,
        current_wl_number INTEGER DEFAULT 0,
        booking_wl_number INTEGER DEFAULT 0,
        chart_prepared INTEGER DEFAULT 0,
        confirmation_probability INTEGER DEFAULT 50,
        risk_badge TEXT DEFAULT 'Moderate',
        prediction_explanation TEXT,
        smart_tip TEXT,
        status TEXT DEFAULT 'TRACKING',
        last_checked_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS pnr_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pnr TEXT NOT NULL,
        status_label TEXT NOT NULL,
        wl_number INTEGER,
        probability INTEGER,
        note TEXT,
        recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(pnr) REFERENCES tracked_pnrs(pnr) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pnr TEXT,
        phone TEXT,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'MOVEMENT',
        status TEXT DEFAULT 'SENT',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) as count FROM tracked_pnrs")
    row = cursor.fetchone()

    if row["count"] == 0:
        print("🌱 [FastAPI DB] Seeding database with realistic sample tickets...")
        now = datetime.utcnow()
        dep1 = (now + timedelta(days=4)).strftime("%Y-%m-%d")
        dep2 = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        # Sample 1: Tejas Rajdhani
        cursor.execute("""
            INSERT INTO tracked_pnrs (
                pnr, phone, train_number, train_name, source_station, dest_station,
                source_station_name, dest_station_name, journey_date, journey_time,
                travel_class, quota, booking_status, current_status, previous_status,
                current_wl_number, booking_wl_number, chart_prepared, confirmation_probability,
                risk_badge, prediction_explanation, smart_tip, status, last_checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TRACKING', ?, ?)
        """, (
            "2458910342", "919876543210", "12952", "New Delhi Tejas Rajdhani",
            "NDLS", "MMCT", "New Delhi", "Mumbai Central", dep1, "16:55",
            "3A", "GNWL", "GNWL 42", "GNWL 18", "GNWL 24",
            18, 42, 0, 84, "High Chance",
            "GNWL on 3A with 4 days remaining has strong historical turnover. 24 berths cleared since booking.",
            "12952 has 11 coaches of 3A (792 berths). Velocity indicates high probability of full berth confirmation before chart preparation.",
            now.isoformat(), (now - timedelta(days=6)).isoformat()
        ))

        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("2458910342", "Booked: GNWL 42", 42, 52, "Initial ticket booking", (now - timedelta(days=6)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("2458910342", "GNWL 31", 31, 64, "Waitlist cleared 11 berths", (now - timedelta(days=4)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("2458910342", "GNWL 24", 24, 73, "Waitlist cleared 7 berths", (now - timedelta(days=2)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("2458910342", "GNWL 18", 18, 84, "Waitlist cleared 6 berths (Current)", now.isoformat()))

        # Sample 2: Karnataka Express
        cursor.execute("""
            INSERT INTO tracked_pnrs (
                pnr, phone, train_number, train_name, source_station, dest_station,
                source_station_name, dest_station_name, journey_date, journey_time,
                travel_class, quota, booking_status, current_status, previous_status,
                current_wl_number, booking_wl_number, chart_prepared, confirmation_probability,
                risk_badge, prediction_explanation, smart_tip, status, last_checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TRACKING', ?, ?)
        """, (
            "4129087563", "919876543210", "12628", "Karnataka Express",
            "NDLS", "SBC", "New Delhi", "KSR Bengaluru", dep2, "20:20",
            "SL", "RLWL", "RLWL 29", "RLWL 9", "RLWL 14",
            9, 29, 0, 72, "Moderate",
            "RLWL quota moves slower than GNWL, but Sleeper class has 12 coaches with significant quota reallocation at charting.",
            "Chart preparation occurs ~4 hrs prior at NDLS. High probability of RAC conversion with guaranteed boarding rights.",
            now.isoformat(), (now - timedelta(days=5)).isoformat()
        ))

        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("4129087563", "Booked: RLWL 29", 29, 44, "Initial ticket booking", (now - timedelta(days=5)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("4129087563", "RLWL 19", 19, 56, "Waitlist cleared 10 berths", (now - timedelta(days=3)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("4129087563", "RLWL 14", 14, 65, "Waitlist cleared 5 berths", (now - timedelta(days=1)).isoformat()))
        cursor.execute("INSERT INTO pnr_history (pnr, status_label, wl_number, probability, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("4129087563", "RLWL 9", 9, 72, "Waitlist cleared 5 berths (Current)", now.isoformat()))

        # Sample Notifications
        msg1 = """🚆 *IRCTC Waitlist Movement Alert!*
🎫 *PNR:* 2458910342
🚄 *Train:* 12952 - New Delhi Tejas Rajdhani (3A)

📉 *Previous Status:* GNWL 24
📈 *Current Status:* *GNWL 18* (Moved up by 6!)
🎯 *Confirmation Chance:* *84% (High Chance)*

⏳ *Next auto-check in:* 2 hours
_Reply STOP 2458910342 to mute alerts._"""

        msg2 = """🚆 *IRCTC Waitlist Movement Alert!*
🎫 *PNR:* 4129087563
🚄 *Train:* 12628 - Karnataka Express (SL)

📉 *Previous Status:* RLWL 14
📈 *Current Status:* *RLWL 9* (Moved up by 5!)
🎯 *Confirmation Chance:* *72% (Moderate)*

⏳ *Next auto-check in:* 2 hours
_Reply STOP 4129087563 to mute alerts._"""

        cursor.execute("INSERT INTO notifications (pnr, phone, message, type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("2458910342", "919876543210", msg1, "MOVEMENT", "DELIVERED", now.isoformat()))
        cursor.execute("INSERT INTO notifications (pnr, phone, message, type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("4129087563", "919876543210", msg2, "MOVEMENT", "DELIVERED", (now - timedelta(days=1)).isoformat()))

    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('mode', 'simulation')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('maintenance_override', 'false')")

    conn.commit()
    conn.close()
