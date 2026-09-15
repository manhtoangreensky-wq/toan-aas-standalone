"""Purge demo data from TOAN AAS Web App & Admin ERP."""
from __future__ import annotations
import os, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from copyfast_db import session_database_path

def purge_demo_data(db_path=None):
    db_file = Path(db_path) if db_path else session_database_path()
    if not db_file.exists():
        print(f"Database not found: {db_file}")
        return {}
    counts = {}
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        cur = conn.execute("DELETE FROM web_ops_followups WHERE id LIKE 'demo-%'")
        counts['followups'] = cur.rowcount
        cur = conn.execute("DELETE FROM web_manual_topup_requests WHERE reference LIKE 'DEMO-%' OR account_id LIKE 'demo-%'")
        counts['manual_topups'] = cur.rowcount
        cur = conn.execute("DELETE FROM web_account_topup_codes WHERE account_id LIKE 'demo-%'")
        counts['topup_codes'] = cur.rowcount
        cur = conn.execute("DELETE FROM web_accounts WHERE id LIKE 'demo-%' OR email LIKE 'demo.%@toanaas.vn'")
        counts['accounts'] = cur.rowcount
        conn.commit()
    print(f"Purged demo records from {db_file}: {counts}")
    return counts

if __name__ == '__main__':
    purge_demo_data()
