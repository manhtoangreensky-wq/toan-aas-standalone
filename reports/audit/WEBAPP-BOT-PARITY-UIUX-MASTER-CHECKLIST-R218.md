# WebApp Bot Parity UI/UX Master Checklist R218

**Ngày lập:** 2026-10-18
**Nguồn tham chiếu:** Bot docs/source/reports đọc-only
**Phạm vi:** WebApp standalone UI/UX, locale, responsive, accessibility, motion và runtime evidence.

## Trạng thái chuẩn

- `[x]` Có bằng chứng đủ trong phạm vi mục đó.
- `[~]` Source đã có nhưng runtime/bridge còn mở.
- `[ ]` Chưa làm.
- `[!]` Blocked hoặc thiếu điều kiện bắt buộc.
- `[→]` Deferred, chỉ mở bằng spec/Owner gate riêng.

## 0. Hàng rào

- [x] Bot chỉ là nguồn tham chiếu; không sửa Bot/Core.
- [x] Không provider call, wallet/PayOS mutation hoặc production-data mutation trong wave UI.
- [x] Giữ palette xanh dương/xanh ngọc và nền navy.
- [x] Không claim output thật từ UI guarded.
- [ ] R218 plan/spec được push vào branch WebApp và CI xác minh.

## 1. Bot authority audit

- [x] Bốn lane SubDub: source subtitle, translated subtitle, translated dubbing, combo.
- [x] Shared source semantic master và translation master được ghi trong design docs Bot.
- [x] Combo dùng `subtitle_copy` và `dub_script` từ cùng translation master.
- [x] Bot có bước preview/quote/explicit confirm trước xử lý có phí.
- [x] Bot có progress, QC artifact, delivery receipt và report.
- [x] Bot có back/retry/failure fail-closed, không tạo job thay thế tự động.
- [x] Bot có nguồn giọng mặc định nam/nữ, giọng đã lưu/tự thêm và Auto speaker.
- [x] Bot có evidence Auto Multi 3–8 và fixture 1/2/3/5/8 người nói.

## 2. SubDub WebApp đang dở — phải đóng trước

- [x] Một workspace dọc rõ ràng: nguồn → lane → cấu hình → báo giá/xác nhận → tiến trình → báo cáo.
- [x] Lane `default_female` hiển thị rõ và có trạng thái guarded.
- [x] Lane `default_male` hiển thị rõ và có trạng thái guarded.
- [x] Lane `saved_voice` có đường sang Voice Library và trạng thái chưa có dữ liệu.
- [x] Lane `custom_voice` mô tả upload + consent + readiness, không giả lập thành công.
- [x] Lane `multi_two` tách khỏi `multi_three_eight`.
- [x] Lane `multi_three_eight` hiển thị giới hạn 3–8 và bản đồ speaker guarded.
- [x] Lane `auto_many` hiển thị tự nhận diện, điều kiện fail-closed và fallback manual.
- [ ] Combo dùng một target language và hai card cấu hình liên kết.
- [ ] Volume original/dubbing có nhãn, giá trị, trạng thái chưa áp dụng và reduced-motion.
- [ ] Báo cáo có request/job/artifact/status nhưng không bịa ID hoặc output.
- [~] Locale VI đã bổ sung copy lane tiếng Việt; cần chạy full locale inventory cho toàn
      SubDub và các lane khác để khóa rò chuỗi còn lại.
- [ ] Locale EN/ZH giữ nguyên nghĩa, không rơi về VI trong các lane mới.
- [ ] Mobile 320/375/390/414/768 không tràn ngang, control ≥44px.

## 3. Các lane sản phẩm tiếp theo

- [ ] Voice: default/saved/custom/preview/speed/volume/consent.
- [ ] Music: background/song/SFX, vocal male/female/duet/auto, quote và result.
- [ ] Image: create/edit/reference/preview/history/output readiness.
- [ ] Video: single/multiscene/long/product, AI/manual boundary, addons và report.
- [ ] Content/Free tools/Projects/Publishing/Memory/Support có flow và empty/error state.

## 4. Runtime and delivery

- [ ] Isolated QA fixture covers every SubDub lane and every guarded failure.
- [ ] Browser AX matrix covers VI/EN/ZH × light/dark × 320/375/390/414/768/1024/1440.
- [ ] Runtime output proves SRT/VTT/audio/MP4 validity when bridge is authorized.
- [ ] Admin sees request/job/artifact/report reference without mutating wallet in QA.
- [ ] Live recheck only after authorized delivery; `MERGED != DEPLOYED != LIVE`.

## 5. Motion (last)

- [ ] Skeleton and step transition do not cause layout shift.
- [ ] Motion uses transform/opacity, 150–300ms micro timing, no linear UI transition.
- [ ] Reduced motion preserves all content and controls.
- [ ] Performance trace records CLS/LCP/INP or an explicit blocker.

## Ledger

```ini
CHECKLIST=WEBAPP-BOT-PARITY-UIUX-R218
STATUS=PLAN_CREATED_SOURCE_AUDIT_COMPLETE
CURRENT_STEP=FINISH_R217_SUBDUB_RUNTIME_GUARDED_GAPS_BEFORE_R218_EXECUTION
BOT_SOURCE_READONLY=YES
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
```
