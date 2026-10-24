# SD-E3 — source crosswalk, chưa phải runtime PASS

BASE79cd75d3d8ee50685bbecd4056f7d84a79f8e68a;PR661/Issue664;
E3contract6380189875;D3receipt6380165981accepted. Independentread-onlyreview
C0/I3/M0;rootactual168QAcomplete/588choices/168Voicereturns/504LFassets/
0interactionerrors-pageerrors-external-UIwrites-overflow. E3FAILED_PENDING_REMEDIATION,
khôngđóngfullE3từbảngsource hoặc collectionexit0.

| SD | Source/UI hiện có | Thiếu UI hoặc T0 phải giữ |
|---|---|---|
| 01 | 4tab/query/ARIA/keyboardhandlers27181/26894 | Actualmode/reload/focus/draft phải cóQA |
| 02 | Filelabel/accept/disabledguard27262 | Upload/preview/metadata/progress/cancel/replaceT0 |
| 03 | Has/no radios+draft27284 | Sourcefile/cue executionT0 |
| 04 | Sourceauto/catalog/disabled27293 | Detection/providerlanguagesT0 |
| 05 | Catalog21/search3panels27107 | Localcatalog khôngphải providertruth |
| 06 | Format/mono-bilingual/cuecompanionlinks27303 | Cueeditor/realoutputT0;Combo selectlabel cólỗiE3-LABEL |
| 07 | Sevenradios flatgrid27224 | E3-GROUP: chưa phânnhómDefault/Saved/Add/Auto theooriginalSD07 |
| 08 | female/male localradio | Engine/defaultvoicereadinessT0 |
| 09 | savedlane→Voice/saved26941 | Profilepicker/preview/default/owner applicationT0 |
| 10 | customlane→Voice/clone/safereturn25945 | Consent/upload/quote/preview/saveprofileT0 |
| 11 | auto_two/distinctauto_speaker_gender | ActualdetectionT0 |
| 12 | auto_multi_3_8/distinctauto_multi_speaker | Count/mappingT0,nofakecount |
| 13 | smart_multi/distinctauto_smart_multivoice | Capability/quality/costT0,C3dedupe khôngphảiengine |
| 14 | Guardedspeakermap27255 | Detect/preview/override/ambiguousDTO T0 |
| 15 | Originalslider+number0–100/validation26915 | 0mutelocal,khôngseparateon-off;mixingoutputT0 |
| 16 | Dub0–200/zeroack27204 | Localmute/outputloudnessT0 |
| 17 | 7positions/line/display/format27212 | E3-LABEL: sourcelineruleselectunlabelled;renderedcueT0 |
| 18 | Readonlysettingsreview27012/stage327428 | E3-EDIT: thiếuSửavềđúngnhóm;duration/cost/expiryT0 |
| 19 | DisabledCTA/reason27460 | Quote/validinputs/submit/progress/retryT0 |
| 20 | Initialempty-onlyreport27472/D3hide | No actualreportDTO/requestjob/file/readiness/recoveryT0 |
| 21 | SafeVoicecontinuation25945/toollinks | Contextfile/subtitle/profile→VideoProjectsAdminT0 |

## Source-confirmed UI findings, không đổ sang T0

- E3-LABEL (Important): portal.js27314–15 `select[name=subtitle_format]` và
  27385–86 Combo `select[name=sub_display_type]` enablednhưngkhôngid/label-for/
  aria-label/labelledby. Nhãnđứngcạnh khôngtạoaccessibleassociation.
- E3-GROUP (Important): voiceLaneHtml27224–46 dựng7radio trongmộtgridphẳng,
  chưaDefault/Saved/Add/Auto grouping;khôngkếtluậnoverflowtừsource.
- E3-EDIT (Important): renderSubDubSettingsRows27012–40 vàstage327437–68
  khôngcóper-groupeditlink/button/focusnavigation. Khôngthêmduration/giá giả.

Root preliminary measuredcontrast finding on actualVI/light320 helpertext:
sourcefilehelp rgb170,184,199onwhite2.02115:1;source-statehelp onteal
1.84162:1;reviewnote onwhite2.02115:1. Rawpartialartifact kept;full168
collectionpending. Decorativearia-hiddenemoji measurements khôngtínhlỗi text.
Final168:483nondecorativetextfails/84unlabelledselectsamples/12rangehitfails
(Combo320pxrange36x44). Raw5937654f...f511e723;existingAXnotemismatch không
táihiện84voicestates nhưngcauseUNKNOWNvẫnmở. Enhancedfindings.jsongiữriêng
viewportWidthvàcontrolwidth,khôngnhầmsốpx. KhôngsửaCSStrướcallowlistRED.

Motion/cuối,engine/provider/wallet/productionkhôngđụng. GoalACTIVE.
