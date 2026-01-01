import sqlite3

DB_PATH = "goals.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # =========================
    # MAQSADLAR JADVALI
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        period_days INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # =========================
    # KUNLIK LOG JADVALI
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goal_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        UNIQUE(goal_id, date)
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
