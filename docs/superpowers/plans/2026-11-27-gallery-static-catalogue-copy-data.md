# Gallery Static Catalogue Copy Data Implementation Plan

> For agentic workers: Antigravity proposal-only theo quy trình Owner đã chọn;
> root giữ vòng đời và nghiệm thu, không cấp Git/VPS/login/settings cho worker.

**Goal:** Chuẩn bị đủ117hàng/351giá trị VI/EN/ZH của nguồn tĩnh Gallery, giữ
nguyên ID/biến/số/ý nghĩa, không ghi ứng dụng ở pha dữ liệu.

**Architecture:** Bốn thư mục worker độc lập, không shared mutable files.
Worker trả JSON; root kiểm ngữ nghĩa một lượt và khóa keyset/source binding.
Không dịch chuỗi người dùng hoặc suy ngôn ngữ bằng thay chữ tổng quát.

**Tech Stack:** Python AST literal extraction; JSON; Antigravity CLI
`gemini-4-hydrogen-xhigh`; root Node assertions.

**Spec:** `docs/superpowers/specs/2026-11-27-gallery-static-catalogue-copy-data.md`.

## Global Constraints

BASE29e0c154; snapshot2026-07-15.1; source b9d32e21.
APP_WRITES=0; không Bot/engine/auth/provider/wallet/PayOS/ENV/data/motion.
Chỉ tên riêng/thương hiệu được giữ trong VI/ZH; mọi từ mô tả thường phải native.
Full MAP trong từng phiếu. Mỗi bước2–5phút; cùng Issue689, không PR trống.

## Task 1 — khóa nguồn và giao bốn phiếu

- [x] Trích `copyfast_free_prompt_gallery.py` bằng AST literal-only:
 7nhóm/20ngành/7goal/9platform,140mẫu; không import ứng dụng.
- [x] Đăng/readback contract7216006483 vào Issue689.
- [x] Giao `GSC-CATEGORIES`21hàng, `GSC-INDUSTRIES-A`40hàng,
 `GSC-INDUSTRIES-B`40hàng, `GSC-TAXONOMY`16hàng qua CLI4ExtraHigh.
 Mỗi phiếu chứa chính xác các ID/field/before và JSON schema after VI/EN/ZH.
 Không lệnh, không appwrite, verify=NOT_RUN.

## Task 2 — nghiệm thu và khóa dữ liệu

- [x] Kiểm đủ117tuple(kind,id,field), mỗi tuple có ba chuỗi khác rỗng;
 before exact source, không thiếu/lặp/thêm key hoặc biến.
- [x] Đọc351giá trị đúng một lượt, nhất quán tên ngành/nhóm và ý nghĩa;
 sai đúng hàng nào thì giao lại đúng hàng đó, không dịch lại cả gói.
- [x] Root verify:
 `node validate-gallery-static-proposals-nov27.cjs`
 trong thư mục evidence của task →117rows/351values/0schema-token-number-errors.
 Lệnh chỉ kiểm dữ liệu đề xuất, không được gọi kết quả đó là UI PASS.
- [x] Khóa receipt/hash và từng nguồn worker; giữ proposal gốc bất biến.

## Task 3 — mở contract ứng dụng khi dữ liệu đạt

- [x] Đối chiếu chính xác consumers/read/copy/save/locale-switch trước app edit.
 Không thay chữ ký shared symbol hoặc payload trước impact scan/contract.
- [x] Tạo RED và allowlist riêng cho một ngôn ngữ nhất quán từ đọc đến lưu.
 App Builder vẫn Antigravity; root chỉ tích hợp, chỉ tự sửa app sau hai lỗi
 cùng acceptance của worker. Không chuyển pha dữ liệu thành phát hành giả.

Runtime contract:
`docs/superpowers/specs/2026-11-27-gallery-native-runtime.md`;
plan `docs/superpowers/plans/2026-11-27-gallery-native-runtime.md`.
Backend RED13/14, currentness RED34/49, taxonomy RED54/54; không lỗi fixture.
Leaf420samples và taxonomy54GREEN đã đạt; transport/server/actions vẫn mở.
Runtime contract mới đang local do publication gate bị chặn; không ghi
nhầm đã đăng cùng contract DATA7216006483.
