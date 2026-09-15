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
    os.environ["WEBAPP_SESSION_DB_PATH"] = str(db_file)
    ensure_copyfast_schema()
    counts = {'accounts': 0, 'profiles': 0, 'topup_codes': 0, 'manual_topups': 0, 'followups': 0, 'notification_runs': 0}
    now = utc_now()
    demo_pwd = 'sha256$demo$e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    demo_clients = [
        ('d0000000-0000-4000-8000-000000000001', 'demo.kh01@toanaas.vn', 'Nguyen Van An (VIP Pro)', '99110001'),
        ('d0000000-0000-4000-8000-000000000002', 'demo.kh02@toanaas.vn', 'Tran Thi Mai (Standard)', '99110002'),
        ('d0000000-0000-4000-8000-000000000003', 'demo.kh03@toanaas.vn', 'Le Hoang Nam (Enterprise)', '99110003'),
    ]
    with sqlite3.connect(db_file) as conn:
        conn.execute('PRAGMA foreign_keys = ON;')
        for acc_id, email, name, code in demo_clients:
            if not conn.execute('SELECT id FROM web_accounts WHERE id = ?', (acc_id,)).fetchone():
                conn.execute('INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, is_active, password_login_enabled, created_at, updated_at) VALUES (?, ?, ?, ?, "user", 1, 1, ?, ?)', (acc_id, email, demo_pwd, name, now, now))
                counts['accounts'] += 1
            if not conn.execute('SELECT account_id FROM web_account_profiles WHERE account_id = ?', (acc_id,)).fetchone():
                conn.execute('INSERT INTO web_account_profiles (account_id, locale, timezone, avatar_style, created_at, updated_at) VALUES (?, "vi", "Asia/Ho_Chi_Minh", "gradient", ?, ?)', (acc_id, now, now))
                counts['profiles'] += 1
            if not conn.execute('SELECT account_id FROM web_account_topup_codes WHERE account_id = ?', (acc_id,)).fetchone():
                conn.execute('INSERT INTO web_account_topup_codes (account_id, payment_code, created_at) VALUES (?, ?, ?)', (acc_id, code, now))
                counts['topup_codes'] += 1
        demo_topups = [
            ('d0000000-0000-4000-8000-000000000001', 500000, 'bank_acb_vietqr', 'DEMO-TOPUP-01: VietQR ACB', 'pending_admin_review', 'demo-idem-001', 'demo-fp-001'),
            ('d0000000-0000-4000-8000-000000000002', 200000, 'momo_tuithantai', 'DEMO-TOPUP-02: MoMo da duyet', 'approved', 'demo-idem-002', 'demo-fp-002'),
            ('d0000000-0000-4000-8000-000000000003', 1000000, 'bank_acb', 'DEMO-TOPUP-03: PayOS da duyet', 'approved', 'demo-idem-003', 'demo-fp-003'),
        ]
        for acc_id, amt, meth, ref, stat, i_key, f_key in demo_topups:
            ih = hashlib.sha256(i_key.encode()).hexdigest()
            fh = hashlib.sha256(f_key.encode()).hexdigest()
            if not conn.execute('SELECT id FROM web_manual_topup_requests WHERE idempotency_key_hash = ?', (ih,)).fetchone():
                conn.execute('INSERT INTO web_manual_topup_requests (account_id, amount_vnd, currency, method, reference, status, idempotency_key_hash, request_fingerprint, submitted_at, updated_at) VALUES (?, ?, "VND", ?, ?, ?, ?, ?, ?, ?)', (acc_id, amt, meth, ref, stat, ih, fh, now, now))
                counts['manual_topups'] += 1
        demo_followups = [
            ('demo-followup-001', 'demo-fp-001', 'runtime_signal', 'demo-src-001', 'd0000000-0000-4000-8000-000000000001', 'operator', 'medium', 'open'),
            ('demo-followup-002', 'demo-fp-002', 'support_triage', 'demo-src-002', 'd0000000-0000-4000-8000-000000000002', 'operator', 'low', 'acknowledged'),
            ('demo-followup-003', 'demo-fp-003', 'runtime_signal', 'demo-src-003', 'd0000000-0000-4000-8000-000000000003', 'manager', 'high', 'resolved'),
        ]
        for fid, fp, sk, sid, aid, role, sev, st in demo_followups:
            if not conn.execute('SELECT id FROM web_ops_followups WHERE id = ?', (fid,)).fetchone():
                conn.execute('INSERT INTO web_ops_followups (id, fingerprint, source_kind, source_id, account_id, required_role, severity, state, source_revision, revision, opened_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)', (fid, fp, sk, sid, aid, role, sev, st, now, now))
                counts['followups'] += 1
        demo_notification_runs = [
            (
                'demo-run-001',
                'demo-req-001',
                'cron_inbox_sweep',
                'slot-20260915-1300',
                'completed',
                101,
                1,
                'hash-demo-001',
                3,
                3,
                '2026-09-15T06:00:00+00:00',
                '2026-09-15T06:00:00+00:00',
                '2026-09-15T06:00:02+00:00',
                None,
                '{"status": "ok", "delivered": 3}',
            ),
            (
                'demo-run-002',
                'demo-req-002',
                'cron_inbox_sweep',
                'slot-20260915-1230',
                'completed',
                102,
                1,
                'hash-demo-002',
                5,
                5,
                '2026-09-15T05:30:00+00:00',
                '2026-09-15T05:30:00+00:00',
                '2026-09-15T05:30:04+00:00',
                None,
                '{"status": "ok", "delivered": 5}',
            ),
            (
                'demo-run-003',
                'demo-req-003',
                'event_topup_notify',
                'slot-20260915-1325',
                'completed',
                103,
                1,
                'hash-demo-003',
                1,
                1,
                '2026-09-15T06:25:00+00:00',
                '2026-09-15T06:25:00+00:00',
                '2026-09-15T06:25:01+00:00',
                None,
                '{"status": "ok", "delivered": 1}',
            ),
            (
                'demo-run-004',
                'demo-req-004',
                'cron_inbox_sweep',
                'slot-20260915-1200',
                'guarded',
                104,
                1,
                'hash-demo-004',
                0,
                2,
                '2026-09-15T05:00:00+00:00',
                '2026-09-15T05:00:00+00:00',
                '2026-09-15T05:00:01+00:00',
                'REPLICA_TOPOLOGY_GUARD',
                '{"status": "guarded", "reason": "topology_unverified"}',
            ),
            (
                'demo-run-005',
                'demo-req-005',
                'manual_maintenance',
                'slot-20260915-1330',
                'started',
                105,
                1,
                'hash-demo-005',
                2,
                4,
                '2026-09-15T06:30:00+00:00',
                '2026-09-15T06:30:00+00:00',
                None,
                None,
                '{"status": "processing"}',
            ),
        ]
        for run_id, req_id, trig, slot, state, fence, pol, ih, actions, cands, dl, started, fin, err, rjson in demo_notification_runs:
            if not conn.execute('SELECT id FROM web_notification_runs WHERE id = ?', (run_id,)).fetchone():
                conn.execute(
                    '''INSERT INTO web_notification_runs
                       (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                        action_count, candidate_count, deadline_at, started_at, finished_at, error_code, receipt_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (run_id, req_id, trig, slot, state, fence, pol, ih, actions, cands, dl, started, fin, err, rjson),
                )
                counts['notification_runs'] += 1
        conn.commit()
    print(f'Done seeding: {counts}')
    return counts

if __name__ == '__main__':
    seed_demo_data()
