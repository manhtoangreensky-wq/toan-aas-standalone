# MU-NATIVE-PRESENTATION-D2 — dọn khối phụ và chỗ trống

23/10/2026 DRAFT, **không BUILD trước D1accepted**. ROOT/branch/Issue664/PR661
theoD1; BASEphảilấylạisaudeliveryD1. B/C/D0locks giữ nguyên, motioncuối.
Ownerđãyêucầuẩnôvônghĩa/toànwebapp; lát này chỉ2nativeMusic/SFXpages.

## Outcome và cách giữ semantics

Initialstate:1visibleformcard/tool thay4, khôngintrostat5/3/0 vàkhôngsidebar
columnrỗng. Validnative resultstate:form+result2cards,3items đủnộidung thật.
Không hiệnemptyresultpanel;form/label/help/explicitCTA đãlàemptyguidance.
Giữ1noteconcise nói đúngđầu ra làvănbản, khôngmôphỏngaudio/player.

Ưutiên footprintnhỏ: scopeddisplay:none chointro/boundary/emptyresult/scope,
khôngxóaDOM/data/receiptownership; addexact2scopeclasses chostylinghooks ở
lastscopepanels, khôngdùngbrittle:last-childnth-childselector. Validresult
khôngbịhide:Music[aria-live="polite"],SFX[data-sfx-cue-sheet-receipt].
Không opacityhack, khôngfocusableẩn:display:none phải loại cảkhỏiAXtree.

Layout2pagesonecolumn,gap16px. SFX giữnativeplacementhelper/boundarynode
đểreceiptvẫninsertBeforeboundary; hiddenboundarykhônggiữtrack. CSSgridareas
chỉform/result, khôngreservedblankcolumn. Không sửaCSSlegacycontract/validators.

SFXrawcue_familyenum cóexactdatahookrồiẩn;metadatachữphẳng thaypillnặng,
giữpreset/ngônngữcóýnghĩa vàmọidata trongstate. Dữ liệu/generatedcontent
theo brief language không bị dịch sangUIlocale hoặc bịcắt. Server-generated
headingmuốnrútgọnphảiđọcpuresourceđểchắcchắnkhôngchecustomusertitle trước.

Formnoteđích dùng một câu đúngsựthật (chốtliteralVI/EN/ZHtrướcfREADY):
Music: nhận3hướngâmnhạcdạngvănbản đểbiêntập, khôngtạotệpnhạc.
SFX: nhận3gợiýhiệuứngdạngvănbản, khôngtạotệpâmthanh.
Tên/nútSFX phảiđúng1cue_sheet/3cues, khônggọi“3cue sheet”.

## Draftallowlist — chốt lại bằng source D1 trước READY

- portal.js:exact2scopeclasshooks/SFXfamilyhook +presentationcopy nếuneeded;
  khôngfunctionsignature/fieldnames/controlattrs/values/stale/normalize changes.
- portal-theme.css:route-scopedhide/layout/metachrome only, khôngglobaltokens/
  shell/navbar/palette/input-focus/motion.
- portal-i18n.js:existingformnote/SFXtitle/submitcopy only nếuREADYchốt.
- Newbrowser/renderer testfile, không weakenoldboundary/grid/safetytests.

Nếu sourcecontracts thật sự mâu thuẫn outcome, dừngphiếu trướcBUILD vàghi
amendment chính xác; không giữdeadcodegiả hoặc nới testđểpass. D1đãkhóa.

## Checklist trước READY

- [ ] D1accepted cùngdeliveryreceipt;BASE/overlay readback đúng.
- [ ] Selector/hook/copy/allowedfiles/codeanchors trọnvẹn, task2–5phút.
- [ ] REDvisiblecards/stattiles/emptyresult vàonecolumn gap; noinput/resultloss.
- [ ] GREENsignedQAinitial1/result2cards, native3items, all5presets, error/
  guard/stale/focus/draft;VI/EN/ZH/lightdark/360..1440/landscape/textscale;
  AXkhôngcònhiddencards/focusables;0errors/overflow/external/unapprovedwrites.
- [ ] Regression/review/docs/Tester/prepush/provenance/newCI/receipt664 trước
  mụctiếptheo. KhôngđóngwholeMusic/Botparity/audio/LIVE.

R1/R2Flash3.8background,Codexreview/verify,noR3. NoAPI/auth/backend/ENV/
wallet/provider/Bot/motion. GoalACTIVE. Đây làDRAFTchờD1, khôngphiếuthựcthi.
