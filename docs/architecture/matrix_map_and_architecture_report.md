# Báo Cáo Ma Trận Chức Năng, Sơ Đồ Điều Hướng & Kiểm Định Trạng Thái TOAN AAS Web App

> **Phiên bản:** 2026.1 Reconciliation Baseline
> **Commit SHA:** 34bc94ef60f75dd749a5f05957db10e262edefad
> **Repository:** manhtoangreensky-wq/toan-aas-standalone
> **Domain:** app.toanaas.vn
> **Quy chuẩn nhận diện:** Teal (#0f766e) / Sky Blue (#0284c7) / Deep Petrol (#063b47)

---

## 1. Ma Trận Trạng Thái Kỹ Thuật (Truthful Feature Readiness Matrix)

| Phân Hệ / Tính Năng | Route Web | UI Present | Route Present | Backend Connected | Live Verified | Trạng Thái Phân Loại | Bảng Giá Dự Kiến / Niêm Yết |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **SubDub Studio (Bóc băng ASR)** | /subtitle<br>/subtitle-studio | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Miễn phí (0 Xu)** |
| **SubDub Studio (Dịch phụ đề)** | /subtitle-studio | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **0.10 Xu / ký tự** |
| **SubDub Studio (Lồng tiếng AI default)** | /subtitle-studio | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **0.10 Xu / ký tự** |
| **SubDub Studio (Lồng tiếng Voice Clone)** | /subtitle-studio | ✅ | ✅ | ✅ | 🟡 | **CONTRACT_READY** | **0.20 Xu / ký tự** |
| **SubDub Multi-Speaker (16 giọng & giới tính)** | /subtitle-studio | 🟡 | 🟡 | ⚡ | ⚡ | **IN_DEVELOPMENT** | *Chưa niêm yết (Đang nghiên cứu)* |
| **Voice Studio & TTS AI** | /voice/tts<br>/voice-studio | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Từ 0.10 Xu / từ**<br>(Voice clone: 1st Free, sau 50 Xu) |
| **AI Music & Sound Effects** | /music/create<br>/music | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **100 - 200 Xu / bài (Nhạc nền)**<br>**200 - 300 Xu / bài (Có lời)** |
| **Video Factory & Storyboard** | /video/create<br>/video | ✅ | ✅ | ✅ | 🟡 | **CONTRACT_READY** | **Theo phân cảnh (Scene-based)** |
| **AI Image Studio 4K** | /image/create<br>/image | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **10 / 20 / 30 / 50 / 70 / 100 / 140 Xu** (7 mức từ Nhanh gọn đến Cao cấp + BH) |
| **AI Document & DeepOCR** | /documents<br>/pdf-vault | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Miễn phí / 3 Xu theo tệp** |
| **AI Marketing & Chat Copilot** | /chat | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Tích hợp phiên làm việc** |
| **Ví Xu & Nạp Tiền VietQR PayOS** | /pricing<br>/packages | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Tự động 5s (+10% Xu)** |
| **ERP Operator & Admin Console** | /admin<br>/workboard | ✅ | ✅ | ✅ | ✅ | **LIVE_VERIFIED** | **Phân quyền RBAC nội bộ** |

---

## 2. Sơ Đồ Điều Hướng & Bản Đồ Dịch Vụ (Service Map)

`
[Public Landing & Pricing] (/ · /pricing · /features)
         │
         ▼
[Authentication & OAuth Gate] (/login · /register · OIDC)
         │
         ▼
[Workspace Command Center] (/dashboard)
         ├──► 🎙️ SubDub Studio (/subtitle · /subtitle-studio)
         │       └──► ⚡ [Đang phát triển]: Phân đoạn nhiều người nói & giới tính
         ├──► 🗣️ Voice Studio & TTS (/voice/tts · /voice-studio)
         ├──► 🎵 AI Music Studio (/music/create · /music)
         ├──► 🎬 Video Factory (/video/create · /video)
         ├──► 🎨 AI Image Studio 4K (/image/create · /image)
         ├──► 📑 Document DeepOCR (/documents · /pdf-vault)
         ├──► 🤖 AI Marketing Copilot (/chat)
         ├──► 💳 Cổng Nạp Tiền VietQR PayOS (/packages · /account/billing)
         └──► 🛡️ ERP Admin & Workboard Operator (/admin · /workboard)
`

---

## 3. Kiểm Định Kỹ Thuật Toàn Diện (Technical Verification)

1. **Brand System Truth**: 100% sử dụng biến semantic tokens chuẩn (--portal-brand, --portal-context, --portal-action, --portal-surface-light, --portal-border).
2. **Canonical Contract Test Suites (113/113 PASS)**:
   - 	est_portal_safety_contracts.py (39/39 PASS)
   - 	est_customer_shell_harmony_contracts.py (3/3 PASS)
   - 	est_workspace_starter_kits_portal_contracts.py (4/4 PASS)
   - 	est_teal_sky_product_redesign_contracts.py (7/7 PASS)
   - 	est_secure_access_first_run_contracts.py (10/10 PASS)
   - 	est_login_app_ux_contracts.py (16/16 PASS)
   - 	est_web_engine_registry_portal_contracts.py (22/22 PASS)
   - 	est_guided_start_capability_navigator_portal_contracts.py (12/12 PASS)
3. **Cơ chế An toàn Zero-Loss**:
   - Tất cả các tác vụ trừ Xu đều yêu cầu CSRF token + Idempotency key.
   - Chỉ trừ Xu khi hệ thống trả về output hợp lệ. Tác vụ lỗi tự động không trừ Xu (ailed_no_charge).
