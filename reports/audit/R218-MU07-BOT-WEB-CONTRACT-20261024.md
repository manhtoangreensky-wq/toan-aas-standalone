# MU07 — đối chiếu từng thao tác Bot và Web

24/10/2026. Web BASE520174941470fab34c60c26e62607ba2d4b3568f,
branchwebapp-r218-billing-ui-20261022/PR661/Issue664. F/H delivered receipt
6372116359;CI40001922044attempt2bothSUCCESS. Goal vẫn ACTIVE;motionLAST.
Bot chỉ đọc snapshot Git0d2f37669732eb2e23a78e75b728172ff41aebbd từ
D:/TOANAAS/wt_music_bot_r1, branchfeat/p0-music-web-canonical-engine-parity-r1.
Không coi snapshot nhánh đó là Bot production hiện tại; không chạy/import/sửa Bot.

## Bot tham chiếu thực sự làm gì

| Thao tác | Bot snapshot | Web hiện tại / gap |
|---|---|---|
| Chọn1/2/3 | bot.py174121..174170: lấy prompt thật trong suggestions, lưu selected_prompt/index; chưa tự đồng nghĩa đã tạo audio | renderMusicCanonicalSuggestions32267/dispatchAction39367/apply39280:Copy/Apply text vào brief; không selectedID server |
| Bộ gợi ý khác | prompt_more174111: offset+=3, gọi music_prompt_suggestions, thay3items/clearselected | Web chưa có next-set/rotation/version DTO; draft lặp lại không được suy thành bộ mới |
| Sửa yêu cầu | edit174094 + inputhandler177018: pendingtext/copyrightvalidation/new3suggestions/resetselected; Back có return_to | Web cho sửa brief thật nhưng chưa chứng minh regenerate3prompt theo mô tả mới |
| Quay lại gợi ý | back_suggestions174073: dùng description/offset/result đã lưu để dựng lại bộ | Web Apply giữ flow.data.draft nhưng estimate thay toàn bộflowdata nên mất quyền quay về bộ trước |
| Quay lại xác nhận | back_confirmation174084 kiểm selected_prompt rồi preview/confirmation | Web không được khôi phục quote/receipt cũ chỉ vì bấm Back hoặc chọn prompt cũ |

Bot music_prompt_suggestions162756..162945 ở snapshot này là hàm chọn ba
hướng từ danh sách style có sẵn theo offset%len(base), không phải tạo audio.
Nhưng Web draft forwards tới internal feature adapter khác; không có bằng
chứng hai contract cùng rotation/no-sideeffect. Không chép danh sách Bot vào
client, không shuffle ba prompt hiện tại rồi gọi đó là “bộ khác”. Rawcallbacks
`music_quick|*` không được gửi từ Web.

## Hợp đồng Web đọc được

Public POST`/api/v1/features/{music_background|music_song}/{draft|estimate|confirm}`
dùng require_csrf. FeatureRequest có inputdict,idempotency_key<=160,
web_quote_receipt<=160;inputserialized<=64000UTF8bytes. Input thực từ form:
background brief/tier/mode/duration;Song thêmlyrics/vocal/lengthmode.

copyfast_api.py7036 forwardsdraft/estimate tớiBotinternal bằng account đã liên
kết. Public planning projection1693/1760 linh hoạt, không strict3suggestions.
Apply chỉ transientMap/mount/focus/toast; không phát generic requestevent.
integration.js38678 thay toàn bộ routeflow khi phase mới trả về. Đây là root
gap UI Back liên-phase; không phải thiếu nhãn nút. Estimate cấp quote receipt
có ghi DBWeb, không tuyên bố draft/estimate literalzero-write.

Chỉ render các prompt thật nhận được, tối đa3, không padding. Metadata field
đã đọc: name,mood,tempo,instrument,duration,vocal,use_case;prompt string hợp lệ
theo canonicalDraftText<=2000 sau trim/NUL removal. Không có batchID/choiceID
hoặc no-effect receipt trong contract được xác minh.

## Phân việc không bỏ sót yêu cầu

1. **MU07-A-RETAINED-OPTIONS (UI):** giữ snapshot tốiđa3gợiý thật trong memory
   của tab/route/session, cho mở “Xem lại các phương án” sau estimate. Chọn
   lại vẫn Apply vào brief và existingquote-stale khóa confirm; không restore
   flow/quote/receipt. Không lưu storage/server, không thay API/gates.
2. **MU07-UI-CHOOSE-EDIT (verification):** actualbrowser phải chứng minh chọn
   prompt1→sửa→chọnprompt2,giữtier/vocal/lyrics/duration/focus;đổiMusicmode/
   Backcùngdocument. Existing source không đủ để tick actualinteraction.
3. **MU07-NEXT-SET-CONTRACT (T0):** trigger“bộkhác”,inputdescription/mode/
   tier/vocal/length/previousset,cursor/version/ownership/expiry,idempotency/
   cost/provider/job/wallet/no-effect evidence,error/retry/output3validitems
   phải được backend authority xác nhận trước khi thêm nút. Không tự mở engine.
4. **MU07-EDIT-REGENERATE-CONTRACT (T0):** newdescription→new3/resetselected,
   validation/originallyrics preservation/copyrightflow/Backcancel;không giả
   việc chỉnhbrief đểbáogiá là đãtạolạibagợiý nhưBot.

MU07 tổng vẫn mở cho đến mọi nhánh có output thật. UI-A không thay thế phần
engine-dependent. Owner yêu cầu UI/UX hết trước, motion kế cuối/UI nghiệm thu,
kỹ thuật/provider/financial cuối cùng và cần authority riêng.

## Bằng chứng READ / giới hạn

- Read-only Bot Gitgrep/show exactpinnedSHA; không dựa lineanchor cũ của repo
  khác. music_prompt_result_keyboard162967..163020 có choose/prompt_more/
  custom/back,previewkeyboard165110..165150 cóedit/back.
- Independent Web audit read-only trả DTO/anchors/callchain, không chạy provider.
- Actual helper+renderer/catalogue probeVIENZH:ordinal1/2/3 đúng,khônglộ{number};
  không sửa helper vì giả định sai.
- Chưa có native regeneration/runtime/output/production/LIVE evidence.
  PROVIDER_CALLS=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
