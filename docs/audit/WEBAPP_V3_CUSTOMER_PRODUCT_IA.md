# Web App V3 Customer Information Architecture (IA) Specification
> **Task**: `P0.WEBAPP.V3.AUDIT.CANONICAL.ARCHITECTURE.TRUTH.CLOSURE`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Base SHA**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`

---

## 1. Architectural Principles

The customer information architecture is redesigned to eliminate catalog flattening and align with the real commercial value proposition of TOAN AAS:

1. **Product-Centric Hierarchy (`TARGET_DESIGN`)**: Customers interact with high-level creative and business solutions, not raw technical subroutines.
2. **Distinct Product Family Separation (`TARGET_DESIGN`)**:
   - **Music & SFX** is strictly separated from **Subtitle/Dubbing/Translation**. They are distinct creative engines.
   - **AutoPost (Publishing Automation)** is a downstream orchestrator consuming common publishable artifacts from any finished producer.
3. **Progressive Disclosure (`TARGET_DESIGN`)**: Primary sidebar provides immediate access to the 10 core product homes. Secondary discovery (tool drawers, format presets, niche calculators) is housed cleanly within product hubs.

---

## 2. Customer Navigation Architecture (13-Item Canonical Sidebar)

The customer sidebar is organized into 4 logical tiers totaling 13 canonical items:

```
TIER 1: CREATIVE ENGINES (PRODUCERS)
  1. /studio         - Video Sản Phẩm AI (Product Video Studio)
  2. /voice          - Giọng Nói & Thuyết Minh AI (AI Voice Studio)
  3. /music          - Âm Nhạc & Hiệu Ứng (Music & SFX Suite)
  4. /subdub         - Phụ Đề & Lồng Tiếng Đa Ngữ (SubDub & Translation)
  5. /tools/video    - Công Cụ Video Thủ Công (Manual Video Tools)
  6. /tools/image    - Hình Ảnh & Tài Nguyên Sáng Tạo (AI Image Tools)

TIER 2: ORCHESTRATION & DISTRIBUTION
  7. /publishing     - Xuất Bản Tự Động & Lịch Đăng (AutoPost)

TIER 3: WORKSPACE & ASSETS
  8. /projects       - Dự Án & Thư Viện Media (Projects Vault)
  9. /tools/free     - Tiện Ích Miễn Phí & Quà Tặng (Free Utilities)

TIER 4: COMMERCE & SUPPORT
 10. /pricing        - Bảng Giá & Nâng Cấp (Pricing & Plans)
 11. /wallet         - Ví Tiền & Nạp Xu (Wallet & Top-up)
 12. /account        - Tài Khoản & Bảo Mật (Account Settings)
 13. /support        - Trung Tâm Trợ Giúp (Support & Tickets)
```

---

## 3. Product Family Disposition & Boundary Contracts

```mermaid
graph TD
    subgraph Producers ["1. Creative Producers"]
        P1["1. Product Video Studio (/studio)"]
        P2["2. AI Voice Studio (/voice)"]
        P3["3. Music & SFX Suite (/music)"]
        P4["4. SubDub & Translation (/subdub)"]
        P5["5. Manual Video Tools (/tools/video)"]
        P6["6. AI Image Tools (/tools/image)"]
    end

    subgraph Handoff ["2. Common Publishable Artifact Contract"]
        H1["Common Artifact (asset_id, sha256, storage_ref)"]
    end

    subgraph Downstream ["3. Downstream Distribution & Vault"]
        D1["7. AutoPost Hub (/publishing)"]
        D2["8. Projects Vault (/projects)"]
    end

    P1 --> H1
    P4 --> H1
    P5 --> H1
    H1 --> D1
    H1 --> D2
```

### 3.1 Detail by Product Family

#### 1. Product Video (`/studio`) — Flagship Producer
- **Current State**: 39 routes in `copyfast_video_studio.py`, 10,215 lines, purely text prompt composition (`INDEPENDENT_SOURCE_VERIFIED`).
- **Target Contract**: Full multi-scene storyboard grid, preflight capability and quote check, confirmation modal, job creation in canonical SQLite `video_jobs` outbox, live scene progress polling, and direct HTML5 MP4 player (`TARGET_DESIGN`).
- **Billing Rule**: Wallet charged ONLY after successful final delivery (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`).

#### 2. Voice (`/voice`) — Independent Audio Producer
- **Current State**: Scattered routes (`voice_studio`, `voice_tts`, `voice_clone`) in general catalog (`INDEPENDENT_SOURCE_VERIFIED`).
- **Target Contract**: Dedicated voice workshop with speaker sample preview, emotion modulation, script pacing controls, and instant MP3/WAV download (`TARGET_DESIGN`).

#### 3. Music & SFX (`/music`) — Independent Audio Producer
- **Current State**: Generic audio presets mixed with video helpers (`INDEPENDENT_SOURCE_VERIFIED`).
- **Target Contract**: Strictly separated from SubDub. Features background music (BGM) generation, sound effect (SFX) cue sheet composer, volume ducking parameters, and audio stem export (`TARGET_DESIGN`).

#### 4. SubDub & Translation (`/subdub`) — Post-Processor & Standalone Tool
- **Current State**: Subtitle viewer without rich timeline editing (`INDEPENDENT_SOURCE_VERIFIED`).
- **Target Contract**: Strictly separated from Music. Provides auto-transcription with SRT/VTT timeline editor, multilingual speech dubbing sync, and burn-in subtitle rendering (`TARGET_DESIGN`). Can consume outputs from Product Video, Video Edit, or user uploads.

#### 5. Manual Video Tools (`/tools/video`) — Fast Utilities
- **Target Contract**: Trimming, merging, aspect cropping, watermark removal, and speed ramping without heavy AI generation overhead (`TARGET_DESIGN`).

#### 6. AutoPost (`/publishing`) — Downstream Orchestrator
- **Target Contract**: Consumes finished media from Product Video, Video Edit, SubDub, or user media uploads. Owns review, approval, multi-channel scheduling (TikTok, YouTube Shorts, Facebook Reels), platform receipt binding, and publish-only retry loops (`TARGET_DESIGN`). Does NOT own video rendering or subtitle generation.

#### 7. Free Utilities (`/tools/free`) — Lead Magnets
- **Target Contract**: Free viral prompt generator, aspect ratio preview calculator, bitrate estimator, and hashtag tools (`TARGET_DESIGN`).

#### 8. Image Tools (`/tools/image`) — Creative Assets
- **Target Contract**: AI product background replacement, thumbnail maker, and sticker generator (`TARGET_DESIGN`).

#### 9. Projects & Media Library (`/projects`) — Unified Vault
- **Target Contract**: Single source of truth for all user-generated media artifacts, version history, and common publishable artifact references (`TARGET_DESIGN`).

#### 10. Account, Wallet & Commerce (`/account`, `/wallet`, `/pricing`) — Commercial Hub
- **Target Contract**: Real PayOS checkout, balance ledger, Telegram account deep-link pairing, and truthful pricing reads via canonical bridge (`INDEPENDENT_SOURCE_VERIFIED`).

---

## 4. Product-to-Publishing Handoff Specification

To prevent tight coupling between producer engines and distribution channels:
1. Producers output a **Common Publishable Artifact** upon final render completion.
2. The artifact is validated for `publish_eligible` (duration, format, resolution).
3. The customer can review, add captions, select channels, and schedule via AutoPost.
4. **Retry Protection**: If publishing fails at the platform level, only the publication attempt is retried. Upstream video rendering is never rerun (`TARGET_DESIGN`).
