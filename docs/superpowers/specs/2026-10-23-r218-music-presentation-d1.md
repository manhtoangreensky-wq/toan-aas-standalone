# MU-NATIVE-PRESENTATION-D1 — chữ đúng ngôn ngữ, helper đọc được

23/10/2026, ACCEPTED_UI_BRANCH_DELIVERY_NO_DEPLOY. Contract/checklist trướcBUILD.
Repo standalone,rootC:/Users/toann/Documents/Codex/_webapp-r218-voice;
branchwebapp-r218-billing-ui-20261022;BASE1144896dde1e957e54de7f1dee361ed927d71529.
PR661/Issue664;dependencyB+D0acceptedreceipt6366118699/CI39960845682bothSUCCESS.
Owner “tiếp tục”, không ô vô nghĩa/thử nghiệm, UIUX trước/motioncuối;
Antigravity3.8Flashnền,R1/R2tốiđa,Codexreview/verify. KhôngIDE/login/settings.

## READ và kết quả duy nhất

Audit `docs/superpowers/plans/2026-10-23-r218-music-presentation-audit.md`:
24configs/48states,4fieldliteralVI,3SFXfixedlabelmixed+2VIfallbacks.
72lighthelperscontrast2.021 trênopaquewhite,72dark5.522;0gradientgópvàonền.
Textarea/select15px;submit44px;radio labeltargets>=103pxheight.
Kết quảD1: cố địnhUIcopy phải theoVI/EN/ZH, helper>=4.5:1, input16px.
Không đổi data languagevi/en, validators, nativePOST, DOMcontrol hoặc cardlayout.

## Allowlist4files và protected

1. static/portal/portal.js: chỉmusicDirectionPresetFields,sfxCueSheetFields
   descriptionplaceholder/help; renderSfxCueSheetResult3dtlabels+2fallbacks.
2. static/portal/portal-i18n.js: đúng9newrows trong2namespace hiện có.
3. static/portal/portal-theme.css: thêm2scopedrules bên dưới, không sửa rulecũ;
   amendmentCI: đặt ngaytrước `/* Final light AI Chat Workspace surface */`,
   không nối sauprotectedfinalChatlayer (testgiữranhgiớiEOF).
4. tests/music-sfx-presentation-copy.test.mjs mới.

Codexquảnlýspec/master/state/checklist/evidence/docs/Tester. Không existingtest
edits, không rename/signature/refactor; khôngnormalizers/fieldnames/options/
required/minmaxlength,outputvalues/stale/sourcebinding/escape,portal shell,
integration.js/A/B/C/D0/API/auth/ENV/data/provider/ví/Bot/motion.

## UIcopy chốt —9rows, fallbackVI tương ứng

| Namespace/key | VI | EN | ZH |
|---|---|---|---|
| musicDirectionUi.field.briefPlaceholder | Ví dụ: nhạc nhẹ, hiện đại cho video giới thiệu ứng dụng. | Example: calm, modern music for an app introduction video. | 例如：为应用介绍视频配上轻柔、现代的音乐。 |
| musicDirectionUi.field.briefHelp | Nêu bối cảnh, người nghe và cảm xúc. Chỉ nhập mô tả, không kèm liên kết hay thông tin riêng tư. | Describe the scene, audience and mood. Enter a description without links or private information. | 描述场景、受众和情绪。只输入文字说明，不要包含链接或私人信息。 |
| sfxCueSheetUi.field.briefPlaceholder | Ví dụ: hiệu ứng nhẹ khi chuyển cảnh và khi hiện lời kêu gọi cuối video. | Example: subtle effects for scene changes and the final video call to action. | 例如：在转场和视频末尾的行动提示处加入轻柔音效。 |
| sfxCueSheetUi.field.briefHelp | Nêu vị trí, hành động và cảm giác cần nhấn. Chỉ nhập mô tả, không kèm liên kết hay thông tin riêng tư. | Describe the placement, action and feeling to emphasize. Enter a description without links or private information. | 描述需要强调的位置、动作和感受。只输入文字说明，不要包含链接或私人信息。 |
| sfxCueSheetUi.result.directionLabel | Hướng hiệu ứng | SFX direction | 音效方向 |
| sfxCueSheetUi.result.mixLabel | Gợi ý hòa âm | Mix guidance | 混音建议 |
| sfxCueSheetUi.result.avoidLabel | Cần tránh | Avoid | 避免事项 |
| sfxCueSheetUi.result.cautionFallback | Kiểm tra quyền sử dụng và bối cảnh trước khi dùng. | Check usage rights and context before use. | 使用前请核对使用权与场景。 |
| sfxCueSheetUi.result.reviewFallback | Rà soát cùng người biên tập trước khi chọn âm thanh. | Review with the editor before choosing audio. | 选择音频前请与剪辑人员共同审核。 |

Fields dùnghelperhiệncó: musicDirectionUiText/sfxCueSheetUiText(key,VI);
SFXdt dùngsafeText(sfxCueSheetUiText(...));fallbackarrays chứahelpertranslated
string rồi escape qua pipelinehiệncó. Khôngdịchcue.direction/mix/avoid/server
title/description/cautions có thật; fallbackreview chỉdefensive, servernormalizer
vẫnrequire>=1review. Testfallback bằngsyntheticpresentationstate ghi rõ giới hạn.

## CSS chốt — chỉ2pages, dùng existing token

```css
:is(.portal-page.portal-music-directions, .portal-page.portal-sfx-cue-sheet) .portal-field-help {
  color: var(--portal-muted);
}
:is(.portal-page.portal-music-directions, .portal-page.portal-sfx-cue-sheet) .portal-form :is(textarea, select) {
  font-size: 16px;
}
```

ĐặtngaytrướcfinalChatmarker đã chỉ định; giữ oldrules sauCRLF→LFnormalization. Khôngimportant/
newvariables/palette/fonts/globalCSS/specificityhack. Nếu computedstyle chưa
đạt, ghiFAILđểreview, không mở rộngselector bừa. Không thêmmotion.

## Bước2–5phút và verify

1. NewESMtest: realcatalogue VM riêng/plainbridge (khôngmutatefrozen.t),
   actual2fieldfunctions+actualSFXresultfunction. Literalexpected9rows/3locales,
   assertfields/schema unchanged; dữ liệu mẫu chỉpresentation, noDTO/outputclaim.
2. Applytestfirst; baselineassertionRED vìoldVI/help/dt/fallback, khôngharness
   ReferenceError. Realfieldfunctions schema2-500/optionsvi/en giữ nguyên.
3. Workereditrecords đúng2fields/3dt/2fallback+9rows+2CSSrules. Codexapplypatch
   sauRED;no otherstatementchange, particularly stale/caution data/escaping.
4. Codexfocused/fullNode/Python21/protectedcomparators; actualsignedQA2routes
   ×VI/EN/ZH×light/dark×390/1440empty+native3result; thêm360/375/landscape/
   textscale/reducedmotion. Measurehelpcontrast>=4.5/inputs>=16/targets>=44.

Commands: `node --test tests/music-sfx-presentation-copy.test.mjs` REDthenGREEN;
`node --test --test-concurrency=2 tests/*.test.mjs` (baseline1016/1016);
Python4native/portalMusic/SFX (baseline21/21); syntax2JS/diff; actualbrowser.
NoBrowserplugin→existingPlaywrightEdgeheadless, no newdependency/visibleIDE.

## Checklist và cổng mởD2

- [x] Dependencyaccepted/READ48states/contrast/touchlabels/sourceinventory.
- [x] Fixedcopy/4fileallowlist/CSS/negativegates trướcBUILD.
- [x] P01 realfunction/catalogue RED→GREEN,9rowsVI/EN/ZH, expected độc lập.
- [x] P02 outsidecopyfields/dt/fallback+9rows/2CSSrules byteequalBASE;
  allnormalizers/A/B/C/D0/integration/API/auth/engine/ví/motion unchanged.
- [x] P03 actualsignedbrowsercopy/noUIlocaleleak/contrast>=4.5/input16,
  3nativeitems/sourcevalues/stale/edit/focus/guard preserved;0unexpectederrors/
  external/unapprovedwrite/overflow; noAPIresponsefixtures.
- [x] P04 focused/full/Python/protected/syntax/diff/review/docs/Tester/prepush/
  provenance/push/readback/newCI/receipt664. ChỉsauacceptedmớimởD2.

Workerone/project,Flash3.8R1/R2maxsameP01,noR3. Source/test/ticket/MAPcôngkhai
stdoutJSONonly, khôngruntimeQA/log/screenshots/DB/secret/tool/Git/ENVsettings.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO;LIVE_PASS=NOT_TESTED;GOAL=ACTIVE;MOTION=LAST.

## Kết quả 23/10/2026

Flash3.8LowR1SUCCESS80.9040656s/1turn; test176lines/source6editrecordsáp
nguyênvăn production; testchỉbỏ1blankEOFprepush. Đây làR1history;
sauCIreopencóR2placementbêndưới, khôngCodexproductionsemanticcorrection.
CleanRED0/5assertionfail→GREEN5/5,
localefocused9/9; fullNode1021/1021; Python21/21; independent86/86,
Critical0/Important0/Minor0.3productionfiles21add/5remove;11protectedfiles
đúngBASE, không đổiintegration/B/C/D0/normalizers/engine/API/auth/ví/motion.

Actualsigned48configs/96states/48nativePOST/3items:helperlight72samples5.797,
dark216samples5.522,input16px;scopeCSS200percenttextstress48overflow0,
khôngOSDynamicTypeclaim. All48downloaded3asset hashesmatchsource,
raw9359f4c4b6a743f56dd0939a996cfe891d118e35d148862a27892922ce0b48dc.
FreshQAedgeguard36/72POST+focus24/24abort/24native retrysuccess3texts;
focusrestored24. Combined108successfulconfiguration-runs/
168explicitPOSTattempts, trongđó108nativetextsuccess,36validguarddenied,
24deliberateabort;không168outputs. Expectednetworkconsole24ghiriêng,
unexpectederrors/external/unapproved/overflow0.

Firstsupplementshared/concurrentQA429compose/registerkhôngđượctínhPASS;
khôngtắtlimit, rerunfreshDB/processsequentialwithD1-specificoutputdirs.
LegacyQAdefaultoutputreuseđãghiđèlênoldlocalraw/PNGs; earliercommitted
audits/receipt/terminalhasheshistorical, khôngnóifilecũcòntạiđó. D1baseline/
greenfilesgiữriêng, allfurtheredgeartifactsdistinctdirs, khôngrestoregiả.
QA3serversallstoppedexit0/tempclean/listeners42644,27983,9713=0.
Evidence `reports/audit/R218-MUSIC-PRESENTATION-D1-QA-20261023.json`.

## CI reopening P04 — CSS placement contract gap, sameD1/R2

HEAD480b25bf push/readback, CI39971274631FAIL atVerify120474294897,
168Pythonpassed/1fail `test_light_chat_workspace_final_surface_keeps_private_authoring_readable`;
authenticatedjobSKIPPED. Actualtest `mobile`regexends\ZinfinalChatlayer;
D1append2rulesatsheetEOFmadeprotectedlayernotendwithitsmobileblock.
Localrepro sameFAIL;Chatdeclarations/test unchanged, notcontrast/runtimefailure.
P04delivery chưa tick, D2khóa. Đây làSPECplacementgap (R1làmđúngphiếuappend),
không resetID/lịch sử hoặc nới testChat. R2chỉdi chuyển2D1rules từEOF về
ngaytrướcmarkerFinalChat. JS/i18n/newtest vàmọiCSSdeclaration/value/specificity
giữ nguyên; Chat/Admin/Productlayersgiữbytes/order. RerunfullfoundationPython,
boundedCIsuiteportable/unchangedLinuxCI+computedbrowser sauplacement trước push.

## R2 local nghiệm thu — cùngSPEC_ID, không vòng3

Flash3.8LowR2SUCCESS39.2298928s/1turn,source-only13965chars/runtimepayload0.
Hai editrecords áp nguyênvăn. Lầnapplyđầu atomicFAILdo thứtựhunkngược;
chỉsắp xếp QApatchhunk tăngdầnrồiáp cùngrecords, khôngđổinội dungthợ.
ExistingChatRED→foundation90/90;independent90/90,1.60s,C0/I0/M0.
FullNode1021/1021,29768.6626ms; boundedCIđúng49selectors395pass/
1POSIXdeselected/16existingwarnings111.08s,exit0. LinuxCIvẫnphảichạy396.
Firstboundedattemptđãhủykhichưacóterminalresult,khôngtínhPASS.

R2actualsigned48configs/96states/48nativePOST3items trênfreshQA2089:
light5.797/dark5.522,input16px,textstress48,0unexpectederror/external/
unapproved/overflow. Raw98c5a6da47b74c18e34edf564d306c47cd42e09617e7a6c0b5554aecf404f8db
trongr2-placement,khôngghiđèR1. NormalizedthemeSHA4eddc847578964eec85ef2f4213d2ad0cd03fc93fa1f4ed11c6c0cf68231759c;
JS/i18nunchanged,all48downloadedassetsmatch. R1guard/focus48+36+24evidence
giữlịch sử;khôngcộnglượtR2thànhuniqueconfigshoặcgiảaudiooutput.
ComparatorcompositionR1six+R2two;11protectedfilesunchanged;alltrackedtests
unchangedvs480b. Removing2D1rulesreproducesBASECSS;entireChatmarkertoEOF
content/orderunchangedAFTERCRLF→LF,khôngrawbyteequalityclaim.
P04vẫnchờnewpush/CIbothjobs/receipt;D2chưamởBUILD.

Finaldelivery:HEAD3e91dbd8/source235a1aa9;CI39975608329terminalSUCCESSboth
jobs120489250057/120490574037,396Linuxcontracts+26runtime;PR661OPEN/CLEAN.
ReceiptIssue664#issuecomment-6368236480,D1tickreadbacktrue/D2open.
P04accepted,khôngredo. ParentD/wholeMusic/audio/Botparity/LIVEvẫnmở.
