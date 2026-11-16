# Phiên PDF-CUSTOMER-CLEANUP-20261116

TESTER_PROJECT_ID=PDF-CUSTOMER-CLEANUP-20261116
TESTER_PROJECT_STATUS=READY
BASE_SHA=2b126b40766404e4b5c0520a121d60c02760d168
TRACKER=Issue689;case source duy nhất DANH-SACH-CASE.md.

| Mã | Nghiệm thu | Bằng chứng |
|---|---|---|
| PC-READY | Ba PDF readyforms bỏ intro/aside, một cột | GuardedHTML exact, form/history/notes giữ |
| PC-LIMITS | Limits thật không bị mất |20MB30trang;Merge2–8/mỗi20MB/tổng40MB30trang |
| PC-RIGHTS | View/run/refresh độc lập stricttrue | Actual fullrenderer3locale/0,1,2sources |
| PC-REFERENCE | Header6px/status14px/pagination44px | Emptycaption bỏ, Previous/Next offsets giữ |
| PC-CUSTOMER | Tên/notes/content/HTML literal | Immutable/escape một lần/hostile translations |
| PC-LOCALE | SameVM/fallback/frozenorder |19newkeys57values/6editedrows18values |
| PC-SOURCE |21literalchanges/exactoutside |22LF/allappPython/CI+1/oldassertions giữ |
| PC-NATIVE |6ownedemptycases375light1440dark | VI Split/EN Merge/ZH Compress/2viewedcrops |
| PC-FIND-CLEAR | Một cặpGET thật,Tab→Find | q=PDF rồiomitq;fields/history/notesexact |
| PC-DATA |9tables/6plans18scenes/source/evidence |0productwrites/reseed/egress/Jobs0 |
| PC-LEGACY | Baselineequivalent/losslessfail giữ | Python29PASS;Node3PASS1sameFAILboth |
| PC-DELIVERY | ExactCI/merge/deploy/runtime/assets | Receipt riêng, khôngsignedoutputclaim |

BASE20tests3PASS17RED→onegroup27files556PASS0FAIL0SKIP46920.245ms.
NativeR1zeroobservations do QA assumed16px;sửa contractR2,khôngworkerfault.
R2preserve measured15pxbaselinefloor,ghi mọi control<16;PDF-INPUT-FONT16
còn mở riêng. Không nhận toànPDFlocale/AX/iOS/font16 hoặcoutputthật.
Guarded/errors/filledoutput/laterpagepagination VM-only nếu chưa native quan sát.
Đã xem2crop;source reviewC0/I0/M0, không chạy lặp nhóm đạt.
