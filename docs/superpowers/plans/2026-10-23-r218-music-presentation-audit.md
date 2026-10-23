# Audit & plan cải tạo — hai trang Music Directions / SFX Cue Sheet

Phạm vi: `/media-workspace/music-directions` và `/media-workspace/sfx-cue-sheet`.
BASE1144896dde1e957e54de7f1dee361ed927d71529;PR661/Issue664. B+D0 đã giao
nhánh/CI39960845682SUCCESS,receipt6366118699; không làm lại các phần đã khóa.
Stack thực: FastAPI + vanillaJS/CSS; không React/Tailwind, không đổi nền tảng.
Bằng chứng: signedQA42644,24cấu hình/48trạng thái/24native textPOSTs,
`../qa/r218-music-presentation-D-20261023/baseline.json` và `contrast-chain.json`.

## 1. Chẩn đoán nhanh

Biểu mẫu hoạt động thật và lỗi/gửi lại/focus đã có evidence. Phần trình bày
vẫn mang dấu vết màn hình kỹ thuật: giải thích giới hạn lặp nhiều khối, 5/3/0
stat tiles không giúp thao tác, và kết quả rỗng chiếm riêng một card. Người
dùng phải đi qua thông tin phụ trước khi làm việc chính. Một số chữ bỏ qua
catalogue, còn màu helperlight dùng giá trị cũ thay vì semantic token sẵn có.

Đang làm đúng cần giữ: palette xanh/navy/ngọc sáng–tối; radio native có label
target lớn; explicitsubmit, draft/stale/guard và focus recovery; nội dung kết
quả từ server được escape, không giả âm thanh/player/provider.

| Tầng | Trạng thái có bằng chứng | Ghi chú |
|---|---|---|
| L0 Brand | Giữ nguyên | Không có lý do đổi màu/font/logo |
| L2 Visual craft | Cần sửa cục bộ | Helperlightcontrast2.021;input15px |
| L3 Content convention | Cần sửa |4fieldstrings và3resultlabels hardcoded;2fallbackVI |
| L4 Cấu trúc | Cần sửa |4visiblecards+intro3stat tiles mỗi trang ban đầu |
| L6 A11y | Một phần đã đạt | Submit44px,labeltargets>=103px;height;focusB+D0xanh;contrasthelperchưađạt |
| P5/P6 Recovery | ScopedPASS |24intentionalnetworkfaults giữdraft/focus vànative retry; không offlinequeue |
| P1/P3/P4 native/PWA | Chưa nghiệm thu máy thật | Không suy từ Edgeviewport ra iOSstandalone/install/keyboard |

Ba câu hỏi app:

- Mất mạng giữa gửi: expliciterrorđúnglocale, draftgiữ,focusphụchồi,gửilạiđượcthật;
  không blindreplay hoặc giảlưu. B+D0runtime24/24.
- Nhận bản vá: CI kiểmSW/buildstamp hiện hành, nhưng bản này chưa deploy và
  chưa đo installedclient update; giữ cổng release/live ởmaster.
- Standalone quay lại: shell/bottomnav hiện có được giữ; chưa test máy đã cài,
  không tuyên bố mọi backgesture đã đạt. Không sửa shell trong D.

## 2. Số đếm được

| Chỉ số | Baseline | Gate mới |
|---|---|---|
| Cấu hình/states |24/48 | Giữ đủVI/EN/ZH,sáng/tối,mobile/desktop |
| Helperlight |72samples,2.021:1 | >=4.5:1 |
| Helperdark |72samples,5.522:1 | Giữ>=4.5:1 |
| Nền helper góp vào contrast |Opaquecardwhite/light;rgb10,45,53dark;0contributinggradient | Không đoán từ ảnh |
| Textarea/select |15px ở2form |16px, không đổi schema |
| Submit |44pxheight |Giữ>=44px |
| Label target radioVI390 |Music103.09–123.23px;SFX128.59pxheight |Giữ>=44px;radio20px không phải toàn target |
| Visibleinitialportal-card |4/tool:form,boundary,emptyresult,scope |D2:1form, không ô rỗng |
| SFX fixedresultlabels |Direction/Mix note/Tránh×3 |TheoUIlocale, data language giữ riêng |

## 3. Lỗi gốc

Sáu defect dưới quy về ba lỗi gốc: copy đi vòng catalogue(UI-03/UI-04), component
legacy không dùng token đang có(UI-01/UI-02), và màn hình kỹ thuật/giải thích giới
hạn được giữ thành nhiều panel(UI-05/UI-06). Không phải thiếu design system toàn app;
không dựng lại token hoặc refactor component chung để sửa sáu điểm này.

## 4. Danh sách defect

| ID / thuật ngữ | Severity / confidence | Nguyên tắc và hệ quả | Fix cụ thể |
|---|---|---|---|
| UI-01 Insufficient contrast |3/Cao |WCAGAA;helperlight khó đọc, hướng dẫn dễ bỏ sót |Scopedhelpercolor=existing--portal-muted,>=4.5 |
| UI-02 Small input text |2/Cao cho15px;TB choiOSrisk |Readableinputs;nguy cơiOSautozoom, chưa đo máy thật |Scopedtextarea/select16px,giữheight/values |
| UI-03 Mixed-locale fieldcopy |2/Cao |Nielsen4;người dùngEN/ZH vẫn đọcVI |4placeholder/help strings→catalogue |
| UI-04 Fixed resultchrome/fallback |2/Cao |Nielsen2/4;UIlabel lệch ngôn ngữ |3SFXdt+2fallback→catalogue, không dịch dữ liệu server |
| UI-05 Redundant separation/vanitymetrics |2/Cao |Nielsen8/Gestalt;3panelphụ+3stat tiles cạnh1form |D2ẩnintro/boundary/empty/scope;singlecolumnkhônggap |
| UI-06 System-centric repeated copy |2/Cao |Nielsen2/8;provider/job/metadata lặp, không giúp làm việc |D2mộtnoteđúngsựthật,metadata phẳng,giữ3resultitems |

## 5. Token đề xuất — tái sử dụng, không đổi brand

| Hạng mục | Hiện tại | D1 đích |
|---|---|---|
| Helperlight |#aab8c7 trênwhite |var(--portal-muted) cósẵn #456b77 |
| Helperdark |existing#83a5ad |Giữrole--portal-muted |
| Helpertype |14px/23.1pxline-height |Giữsize/leading, chỉsửacontrast |
| Textarea/select |15px |16px của4ptscale |
| Layoutgap |legacy18px |D2cục bộ16px,khôngđổi toànapp |

Không tạoTailwindconfig/CSSvariables mới: dự án là vanillaCSS và đã có token.

## 6. Lộ trình có dependency

1. `MU-NATIVE-PRESENTATION-D1`: literalcopy+contrast/inputfont.4fileBuilder,
   source/test/CSS gates +actualbrowser +docs/delivery. KhôngẩncardởD1.
2. `MU-NATIVE-PRESENTATION-D2`: sau D1accepted, ẩnkhối phụ,giữform/kếtquả thật;
   CSSscoped+DOMstylinghooks tối thiểu, không sửaAPI/validator/placementhelper.
3. Motion chỉ sau toàn bộ UI/UX checklist, không thêm trong D1/D2.

## 7. Prompt cho worker — tách theo spec

```text
Implement D1 only from its complete spec and exact source packet. Preserve
all schema, validators, fields, routes, native radio/submit attributes and
result content. Localize only nine fixed UI strings. Reuse existing muted
theme token for help and use16px textarea/select only on the two forms.
Write real field/renderer tests first; Codex runs RED, then applies source.
Do not hide panels or change layout in D1. No tools/Git/provider/wallet/auth.
```

```text
D2 stays DRAFT until D1 accepted. Keep functional DOM/data/receipt ownership.
Hide only the identified secondary/empty blocks with scoped display:none,
remove reserved grid space, and retain a concise truthful text-output note.
Keep actual result items, native input/submit behavior, stale state and focus.
No backend/API/engine/provider or motion work. Detailed packet before BUILD.
```

## 8. Checklist nghiệm thu

- [x] Baseline24configs/48states vàopaquebackground/touchlabelmeasure.
- [x] D1nineUIstrings VI/EN/ZH, không thay nguồn/ngôn ngữ dữ liệu server.
- [x] Helpercontrast>=4.5 hai theme; textarea/select16px,labels/submit>=44px.
- [x] D1/D2realnativeflow vẫn3items, error/guard/stale/focus/draft không mất.
- [x] D2initialvisiblecard1, resultstate2; khôngsidebarcolumnrỗng/stat0/audiofake.
- [x] 360/375/390/768/1440/landscape vàreducedmotion/textscale browser checks.
- [ ] Source/regression/Python/browser/review/prepush/CI/receipt trước mỗi bước.

## 9. Chưa kiểm được / ngoài phạm vi

RealinstallediOS/Android, bànphímảo/standaloneback/update; LCP/INP/CLS trace;
productiondeployment/LIVE; generation/player/download/save/reuse/canonicalaudio/
Botparity vàM0. Không lấyUIclean hoặcHTTP200 để đóng những mục này.
