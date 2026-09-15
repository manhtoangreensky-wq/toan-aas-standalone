"""Seed demo data for TOAN AAS Web App & Admin ERP."""
from __future__ import annotations
import hashlib, os, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from copyfast_db import ensure_copyfast_schema, session_database_path, utc_now

def resolve_target_db(db_path=None):
    if db_path:
        return Path(db_path)
    if os.environ.get("WEBAPP_SESSION_DB_PATH"):
        return Path(os.environ["WEBAPP_SESSION_DB_PATH"])
    if Path("/data/toandaas_webapp_session.db").exists():
        return Path("/data/toandaas_webapp_session.db")
    return Path(session_database_path())

def seed_demo_data(db_path=None):
    db_file = resolve_target_db(db_path)
    ensure_copyfast_schema()
    counts = {'accounts': 0, 'topup_codes': 0, 'manual_topups': 0, 'followups': 0}
    now = utc_now()
    demo_pwd = 'sha256$demo$e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    demo_clients = [
        ('demo-kh01-id', 'demo.kh01@toanaas.vn', 'Nguyen Van An (VIP Pro)', '99110001'),
        ('demo-kh02-id', 'demo.kh02@toanaas.vn', 'Tran Thi Mai (Standard)', '99110002'),
        ('demo-kh03-id', 'demo.kh03@toanaas.vn', 'Le Hoang Nam (Enterprise)', '99110003'),
    ]
    with sqlite3.connect(db_file) as conn:
        conn.execute('PRAGMA foreign_keys = ON;')
        for acc_id, email, name, code in demo_clients:
            if not conn.execute('SELECT id FROM web_accounts WHERE id = ?', (acc_id,)).fetchone():
                conn.execute('INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, is_active, password_login_enabled, created_at, updated_at) VALUES (?, ?, ?, ?, "user", 1, 1, ?, ?)', (acc_id, email, demo_pwd, name, now, now))
                counts['accounts'] += 1
            if not conn.execute('SELECT account_id FROM web_account_topup_codes WHERE account_id = ?', (acc_id,)).fetchone():
                conn.execute('INSERT INTO web_account_topup_codes (account_id, payment_code, created_at) VALUES (?, ?, ?)', (acc_id, code, now))
                counts['topup_codes'] += 1
        demo_topups = [
            ('demo-kh01-id', 500000, 'bank_acb_vietqr', 'DEMO-TOPUP-01: VietQR ACB', 'pending_admin_review', 'demo-idem-001', 'demo-fp-001'),
            ('demo-kh02-id', 200000, 'momo_tuithantai', 'DEMO-TOPUP-02: MoMo da duyet', 'approved', 'demo-idem-002', 'demo-fp-002'),
            ('demo-kh03-id', 1000000, 'bank_acb', 'DEMO-TOPUP-03: PayOS da duyet', 'approved', 'demo-idem-003', 'demo-fp-003'),
        ]
        for acc_id, amt, meth, ref, stat, i_key, f_key in demo_topups:
            ih = hashlib.sha256(i_key.encode()).hexdigest()
            fh = hashlib.sha256(f_key.encode()).hexdigest()
            if not conn.execute('SELECT id FROM web_manual_topup_requests WHERE idempotency_key_hash = ?', (ih,)).fetchone():
                conn.execute('INSERT INTO web_manual_topup_requests (account_id, amount_vnd, currency, method, reference, status, idempotency_key_hash, request_fingerprint, submitted_at, updated_at) VALUES (?, ?, "VND", ?, ?, ?, ?, ?, ?, ?)', (acc_id, amt, meth, ref, stat, ih, fh, now, now))
                counts['manual_topups'] += 1
        demo_followups = [
            ('demo-followup-001', 'demo-fp-001', 'runtime_signal', 'demo-src-001', 'demo-kh01-id', 'operator', 'medium', 'open'),
            ('demo-followup-002', 'demo-fp-002', 'support_triage', 'demo-src-002', 'demo-kh02-id', 'operator', 'low', 'acknowledged'),
            ('demo-followup-003', 'demo-fp-003', 'runtime_signal', 'demo-src-003', 'demo-kh03-id', 'manager', 'high', 'resolved'),
        ]
        for fid, fp, sk, sid, aid, role, sev, st in demo_followups:
            if not conn.execute('SELECT id FROM web_ops_followups WHERE id = ?', (fid,)).fetchone():
                conn.execute('INSERT INTO web_ops_followups (id, fingerprint, source_kind, source_id, account_id, required_role, severity, state, source_revision, revision, opened_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)', (fid, fp, sk, sid, aid, role, sev, st, now, now))
                counts['followups'] += 1
        conn.commit()
    print(f'Done seeding: {counts}')
    return counts

if __name__ == '__main__':
    seed_demo_data()
