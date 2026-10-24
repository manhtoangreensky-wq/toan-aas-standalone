# SubDub — kế tiếp Music, khóa UI trước motion

BASE06afc2c3abc554e69c7be36604fee310f877c8c6;PR661/Issue664.
MU07-A accepted receipt6373888334/CI40016578805bothSUCCESS,456records.
GoalACTIVE;motionLAST. ExistingSD-B2/C2/D2/E2 remainprotected, do notredo.
VanillaJS/FastAPI/existingblue-nav-teal;notNext/Tailwindmigration.

> note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt
> để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec
> phức tạp thì làm từng spec.

## SD01..21 — không bỏ requirement hoặc giả engine

| SD | UI đã có / cần giữ | Phần còn làm / bằng chứng cần có |
|---|---|---|
| 01 | Fourtabs/inplace/query/keyboard;current48oneactive | Khôngredo; tiếp tục protectedbrowser |
| 02 | Sourcefiledisabled/readinessmessage | Upload/preview/replace/cancel/metadata authorityT0;UI chỉ dọn lặp, không bật filegiả |
| 03 | Has/no subtitle radio,sharedcapture | Actual48sourcechoice/capture bổ sung trong finalSDmatrix |
| 04 | Sourceauto/canonical21disabled | Không mở khi chưaDTO; auto-detect kháclocale;T0execution |
| 05 | 21targetlanguages VI/EN/ZH-first,customISO | SD-B3font16;SD-B4search21/keepselection/noeffect;nativeexecutionT0 |
| 06 | Formats/SRTVTTTXT/mono-bilingual/permode | Cueeditor/source-original-translated contractT0;UI label/reviewfinalmatrix |
| 07 | Sevenlane choices localdraft | SD-C3grouping/no duplicateSmartcard;keepall7/notcapabilityclaim |
| 08 | defaultfemale/male | Actualkeyboard/readiness;defaultdoesnotneedsavedprofile |
| 09 | savedlink→Voice | Picker/applicationreceipt/ownerreadinessT0;donotfakeprofileID |
| 10 | clonelink/returncontinuationaccepted | Consent/upload/preview/savecanonicalT0;C2draftprotected |
| 11 | auto_two callbackdistinct | UI lane kept;detection/count/outputT0 |
| 12 | auto_multi_3_8 callbackdistinct | UI lane kept;nocountfake;mappingT0 |
| 13 | smart_multi callbackdistinct | Remove repeatedunusedbox onlybySD-C3;realcapability/quality/costT0 |
| 14 | empty speaker-map alreadyhidden | No rows without realdata;ambiguous/override/reportT0 |
| 15 | original0–100number/range | SD-D2locked;0/100/mute/captureprotected |
| 16 | dub0–200number/range/ack | SD-D2locked;0/200/invalid/muteprotected |
| 17 | sevenpositions anddisplay | Allsubtitlemodeoptions/capture/reviewfinalmatrix;engineformatT0 |
| 18 | Settingsreviewregion/accessibility | SD-D3remove meaninglessunknowncostduplication without hiding a realquote;canonicalquoteT0 |
| 19 | executionCTAguarded | Do notenable/no fakequote/progress;realadmissionT0 |
| 20 | emptyreportinitialcard | SD-D3omit initial emptysection;preserve future error/status output;outputreadinessT0 |
| 21 | Voicecontinuation + companions | C2locked;context/profile/file/reusecontractT0;actualreturnprotected |

## Ordered executable queue

| Order | Spec | Observable outcome | Dependency | Run |
|---|---|---|---|---|
| 1 | SD-B3-INPUT-FONT | All visible SubDub text/select/number/file inputs >=16px,values/layout/gates unchanged | MU07-Aaccepted | SIMPLE/SINGLE |
| 2 | SD-B4-LANGUAGE-FINDABILITY | Search21localizedcodes/labels,selectionneverchangesfromsearch,clearsafely,keyboard/noresults | B3accepted | COMPLEX/SINGLE;formalcontractbeforeBUILD |
| 3 | SD-C3-VOICE-CLARITY | Sevenchoicesremain;Smartexplanationonce,noduplicateinertbox;Voicecontinuationunchanged | B4accepted | Bounded;formalcontractbeforeBUILD |
| 4 | SD-D3-EMPTY-REVIEW | Noinitialemptyreport/meaninglessfinancialcells;realstatusnotconcealed | C3accepted | Bounded;formalcontractbeforeBUILD |
| 5 | SD-E3-FINAL-UI | Fourmodes×VIENZH×themes×mobile/tablet/desktop/landscape;all21requirementsmapped;keyboardAXcontrast/nooverflow | B3..D3accepted | QA;noengineproof |
| 6 | SD-D4-ORIGINAL-AUDIO-TOGGLE | OriginalSD15Bật/tắtriêngstillOPEN;0%mutealreadytestednotfullcontrolcompletion. Botsemantics/spec/REDbeforebuild | E3scopeddeliveryaccepted | COMPLEX/SINGLE,beforeImage |
| T0 | SD-CANONICAL-GAPS | upload/ASR/translation/voices/speakers/quotes/jobs/output/recovery | UI/motiondone+authority | technicalnotfakeUI |

Firstspec `docs/superpowers/specs/2026-10-24-r218-subdub-input-font.md` accepted
receipt6374462006/HEAD4d66ef14/CI40020963811bothSUCCESS. Next B4 exact spec
`docs/superpowers/specs/2026-10-24-r218-subdub-language-findability.md`,
contract6374610644;acceptedreceipt6379454063/HEAD89f6d6fe/CI40027725649
bothSUCCESS/456records. CurrentC3spec2026-10-24-r218-subdub-voice-clarity.md,
contract6379509521/oneCSSrule/actualQA;C3deliveredHEAD00a34c2b/
CI40061704379bothSUCCESS456records/receipt6379877100. D3nowunlocked;
spec2026-10-24-r218-subdub-empty-review.md/contract6379928009,
only2placeholderattributes+2scopedCSSrules/failopenonadditionaloutput.
 D3deliveredSOURCEd643ce55/HEAD79cd75d3/CI40063985662bothSUCCESS456/
receipt6380165981. E3contract6380189875/READ168complete;localLABELR1+
CONTRASTR2gatespassed48/768helpers/min8.83653/unknown0. NextRANGE→GROUP→
EDIT→READINESSaudit→final168;nochildpush,oneE3batchafterlocalgates.
RANGEnowLOCALpassedcontract6380830198/actual72+supplement24/phone48min200x44/
desktop24exactgeometry/192VoiceReturns48modeRoundTrips/Node1281/Python21/
sourceC0I0M0. GROUPnowLOCALacceptedcontract6381189391:4borderlesssemanticgroups,
7visiblechoices/fullARIAreview;actual84/588click588arrow168VoiceReturns,
36heightcomparatorsallshorter/1092AAmin8.836529/252LFassets/errors0.
Supplement84voice+84nonvoice closesgeometry/globalvisibilityreviewgaps;
source+supplementC0I0M0/Node1287/Python21. R1R2gatefailed,noinvalidartifact
applied;Solxhighpacket/newunitonly,R1JS+SPEC CSSpreserved/noR3.
E3-EDITnowLOCALacceptedcontract6381974676/amendments:review→actualsettingfocus,
E607no-opHTMLguard/E608instantcenteronlyafteractualRED. Final168/1218click/
336keyboard1050edits168VoiceReturns/504LFassets/errors0/Node1295/Python21/
sourceC0I0M0/exact10records. NextREADINESSformalcontractforretainedUNKNOWN,
thenparentfinal168/Tester/docs/provenance/oneE3push/exactHEADCIreceipt.
Eachspec getsownAC/RED/protectedcomparator/Testercases/evidencebeforecode.
AntigravityFlash3.8R1/R2max→sameSPEC_IDSolxhighonlyaftertwofailures/noR3.
Singleworker/sharedsource;Codexreview/actualbrowser/onebatchdelivery.
Thisplan doesnotcloseallSD/Music/master,productionorMotion.
READINESSnowLOCALaccepted26a966e2/receipt6383548657/native72/pending12/
stable168/Node1301;parentfinal168unique/allstrictcounters0/672LFassets/
14448leaftextsmin5.223799/168rangesmin200x44/raw249be2cf…34782a.
IndependentTesterREADY_FOR_SCOPED_LOCAL_ACCEPTANCE/report9b5f29a4…3e82b9;
notall21requirementsdone. Deliverynextmaincompat0e1b49b5SFX#663/exact2
provenanceconflictsonly/keepUI4assets+main5files;Webonlyrefresh/ONEpushCI.
TesterE3finalreadfoundSD15dedicatedon/off absent;retainedasUIgapD4above,
notT0andnotdiscarded. E3 nowdeliveredHEADba4b2dfa/CI40092099397/receipt6384081882.
SD-D4samecounter2FlashR1R2artifactfails→SolxhighNEW_TESTonly;productionfrozen9.
ActualRED6assert/0harness→GREEN6/focused80/fullNode1307/Python85+1deselected/
2existingwarnings. Main48/96VoiceReturns/48modeLoops/text2x/192assets/counters0.
Supplement42finalclassification/independentTester/docs/provenance/onedelivery
remainOPEN;do notstartImagebeforeD4localacceptanceanddeliverygate. No motion.

READactual48rawSHA712cd264586acda482a62391ec380b93b17ee242ad0f83639f13073a1ed7c155:
noerrors/external/UIwrites/overflow;36targetstatesfont15andnosearch;
24dubbing/comboSmartboxesduplicateparagraphs;48visibleemptyreportcards.
Botpin0d2f376...42551 has21targetcodes+auto;236935/238376quickkeyboard5+custom;
21Webtargets match sourcecatalog,notallproviderlanguagesorproductiontruth.
PWAoffline/SWupdate/nativekeyboard/OStextscale/standalonedevice notmeasured
inthisREAD;keepglobalfinalQArequirementsopen,motionfinalwaveuntouched.
