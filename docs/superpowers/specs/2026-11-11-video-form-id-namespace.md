# Video form ID namespace — bounded accessibility contract

SPEC=VIDEO-FORM-ID-NAMESPACE; BASE_SHA=b1a48e09f9f3aa5882f2861feaafdfef1d327e2d.
Branch=codex/video-form-id-namespace-20261111; tracker Issue689.
Prior PR717 code/deploy/runtime/assets verified, no repeat of54viewUI QA.

Goal: clicking a scene label focuses that scene's own input; control/label/help
IDs remain unique across plan edit, scene create and every scene edit form.
Actual prior owned localhost diagnostic:9duplicateIDgroups; title/tags each5,
7scene fields each4; scene-title label.control!==owninput. This is aBASEbug,
not a regression from the prior clutter patch.

Approach: reuse renderFields' existing optional fifth idNamespace parameter.
Allowed application edits only4call-expression replacements in portal.js:
plancreate ->video-plan-create; planupdate ->video-plan-<validatedplanUUID>;
scenecreate ->video-scene-create-<validatedplanUUID>;
sceneupdate ->video-scene-<normalizedsceneUUID>. Same helper, no new state.
No signature/helper/normalizer/HTML fieldname/action/route/confirmation/value/
disabled/required/options/CSRF/revision/session/backend/schema/data/i18n/CSS/
motion/provider/wallet/Bot/route-engine/ENV/deployworkflow changes.

Application allowlist static/portal/portal.js exact4callsubstrings only.
Tests: new tests/video-form-id-namespace.test.mjs plus one CI command invocation;
ops/original-feature/cases/Tester and generatedTesterlocal-file metadata/provenance
may update. No productiondata/provider/financial writes; paidcalls0.

## Ordered checklist

- [x] Real-renderer RED:3scenes/5forms,VI/EN/ZH,draft/readonly/approved/archived;
  unique document IDs, label points exactly one ownform control, helpIDs resolve.
- [x] One Antigravity3.8FlashHigh output-only R1, fullpublicMAP included.
- [x] Exact4callpatch review; allother application bytes/19protectedpaths unchanged.
- [x] Targeted27GREEN, baselineprotocol parity excludes only id/for/aria-describedby;
  allnames/values/options/actions/labels/disabled/records identical.
- [x] Native3locales×320/1440 on actual savedplan with3scenes, plus listview;
  click labels and verify native .control/focus owninput, no productwrites.
- [x] CopiedQA6plan18scene/hash/evidence unchanged, sourcebinding,30ownedJobprocesses->0.
- [x] Ops/original-feature/canonicalcases/Tester/filemetadata ready;metadata1pass.
  Web-onlysourceprovenance14296e95c273ef33fb112b22cfb8f1bbca2f94d9,
  fingerprintfd4adb0091d9116016e9c7b677477f12404013418e4a2c120ba33399c1b79f66.
- [ ] ExactHEADCI/merge/exactSHAdeploy/runtime/assets receipt on Issue689.

Acceptance keeps real labels and description associations, not invisible ARIA
workarounds or removing inputs. readonly/archived labels keep correct .control;
native click-to-focus asserted only when owncontrol enabled. No output-provider
claims. Fixtures are isolated synthetic; no runtime production/customer data sent
to worker. All earlier UI/data evidence retained; only this ID/focus gate rerun.

Commands: node --test tests/video-form-id-namespace.test.mjs ->27passed after
patch; node --check static/portal/portal.js ->exit0. Coordinator compares real
rendered controls before/after with id/for/aria-describedby normalized only.
Ownedlocalhost Chrome/Playwright (Browser plugin absent); productionbrowser
disabled, no alternatebrowser/login/settings bypass. No trueSafari/deviceclaim.

WorkerR1 then sameSPEC R2 if actualfailure, no directapplication implementation
before2genuinefailures; spec/harness omissions attributed tocoordinator. No global
lesson promotion. Fullgoal remains active: rawtags/oldrecords/titlelimits,
otherplanners/currentinput/stale/retry/auth/device/signedLIVE andmotionlast open.

Native12/12views passed:336native label/controlassociations+336actual labelclick
focuschecks;0disabledcontrols/0valuechanges,12screenshots. KeyboardTabseparate,
no focus()fallback. Sourcebinding,originalevidence anddatahash
ffe814d2a5b4fcbf45e2dc330bab577edbec4a5eb881a3b2d1799104e5bedf44 preserved,
6plan18scene/quickcheckok;0compose/save/egress/.env/media/provider/wallet/production.
UIlayout/contrast previouslyaccepted retained, no54viewreplay. One representative
VI320lastscene screenshot inspected; rawgeneratedtags stillvisible ineditfield,
explicitly nextmetadata-editpresentationtask, not claimedpurified bythisIDfix.
