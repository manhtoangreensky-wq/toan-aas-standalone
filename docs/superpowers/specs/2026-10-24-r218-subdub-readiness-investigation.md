# E3-READINESS — observe real bootstrap and early edits before any fix

SPEC_ID=E3-READINESS;PHASE=READ;ROOTC:/Users/toann/Documents/Codex/_webapp-r218-voice.
BASE_SHA=7e35f0ab78a32b2d4d7bffc7536a4dd381c21151
BRANCHwebapp-r218-billing-ui-20261022/PR661/Issue664.
DependsEDITLOCALacceptedreceipt6382683426;GROUP6381890971/RANGE6381116731/
LC6380807646 also LOCALaccepted. Nochildpush;oneE3deliveryafterallgates.
OwnerorderedcompleteUI/UX,unfinishedfirst,motionLAST. GoalACTIVE.

## Retained unknowns, no retroactive root-cause invention

U1:C3EN/dark844Dubbing AX-note literal mismatch;originalfailure snapshotmissing.
U2:LCVI/dark1440source line-rule review mismatch beforeactualauthbootstrapwait;
originalglobalstate/AXsnapshotmissing. Stablewaitrerun passed, not diagnosis.
E607blur-no-op-remount andE608stickyfocus were separate observedEDIT bugs;
theirREDGREENdoesnotexplainU1/U2. Preserve historicalUNKNOWN even if new
related defect has a proven root cause; classify coverage limits explicitly.

## READ source boundary

copyfast_pages.py600..620 shell payload contains public route/locale/API URLs,
not signed account orCSRF. portal.js mounts initially before integration.js;
mountPortal calls synchronizeSubDubWorkspaceDraftSession, then main.innerHTML.
SubDub localcontrols currently renderenabled independent of session. capture
returnsnull while subDubWorkspaceDraftSession empty. Summary reads snapshot.
integration hydrate starts with merge and awaitPromise.all catalog/status/me/
providers/Telegramstatus; signed account+csrf projection merges afterwards.
synchronizeSubDubWorkspaceDraftSession clears SubDub draft onmissing/changed
token. These are source observations, not runtime early-input loss proof yet.
Current secureidentity fence is protected; do not carry anonymous drafts into
another account or change auth/CSRF policies to make UX pass.

## Scope/allowed/protected

READonly:externalQA scripts/artifacts under
C:/Users/toann/Documents/Codex/qa/r218-music-review-FH-20261024;
formal spec/checklist/evidence/master/state/tracker updates only.
ALLproductioncode/oldtests/auth/integration/backend/Bot/engine/provider/wallet/
ENV/DBschema/Chat/motion locked. No code fix before newboundedcontract/RED/
Flash3.8R1(noR3aftertwofails). No installs/IDE/window/login/logout/settings.
ExistingheadlessEdge/Playwright:Browserplugin unavailable. Realserverwith
temporaryDB/assets,bridge/provider/PayOSOFF;authregistration/locale onlyQA.

## Ordered tasks (2–5min pieces, single read-only audit)

1. Record source lifecycle above, publicshell→initialrender→unsignedmerge→
   authenticresponse→signedprojection/remount/draftsession. Only booleans,
   timestamps andsyntheticcontrolvalues;neverserialize token/accountresponse.
2. Hold ONLY real /api/v1/auth/me response after fetching it from isolated
   localhost. Fulfill the same real response afterexplicitrelease; no fake
   account/session/CSRF/capability, no forcing READY or dispatching mount.
   Initial app load toDOMcontentloaded, notnetworkidlewhileholdingresponse.
3. Actual36earlyscenarios=4modes*VIENZH*3views390x900/844x390/1440x900,dark.
   CoversoriginalU1EN844/U2VI1440 plusmobile. NewQA profile perlocale/context.
   Interact only visiblyenabled normalcontrols before real authresponse:
   source-statewithsubtitles;SourceOnlyline-ruleshort+formatVTT/positiontopright;
   non-source targetja/custompt-BR;Dub/Combo customvoice/original0/dub200;
   subtitlepositions/layout/format as available. Read immediatecontrol/review,
   semanticAX/noteDOMstate/readinessbooleans;releaseauththen read again.
   Allfieldsettings use publicliteraltestvalues, no files/providerprofileIDs.
4. Stable36matchedscenarios:wait actualauthenticated/nonemptyCSRFbootstrap
   before same interactions, then capture immediate+post-networkidle state.
   Comparemode/selectedvalues/review/AX without globallydisabling assertions.
   Record exact original U1/U2 dimensions/locale/routes and repeatednoteAX.
5. Persist per-case raw scopedDOM/AX/events/mount-marker identities and failure
   context BEFOREclose, uniqueoutputfolders so RED/GREEN neveroverwrite.
   Allrequestoutside/unknown/mutationblocked+logged;page/console/overflow.
   Use LF asset hashes to match checked-inHEAD, notcachedprevioussource.
6. Report observedfindingIDs/rootcauses vsunknownhistoricalitems separately.
   A collectionexit0 is NOT UX acceptance if loss/mismatch observed. Any UI
   fixneeds boundedamendment/actualRED/Flashfirst/testonlyRED→GREEN/review.

## Observable acceptance and stop gates

R701:source boundary map exact anddocumented, protectedsource unchanged.
R702:36early+36stable scenarios; fullactualresponse-onlydelay provenance,
before/after settings+review/readiness andnewrawAX, allapp errors counted.
R703:each observed mismatch gets current reproducible input+state+cause or
UNKNOWN;no oldsnapshot invented. U1/U2 marked reproduced/notreproduced with
limits,neverclosedmerelybywait/rerun. Scopefixcontractbeforebuildifneeded.
R704:finaldecision crosswalk kept inmaster/state/Issue664;nextparentfinal
E3/Testerdocs/provenance/onepushonlywhen requiredcurrentUIgates met.
Noengine/nativeSafari/OStextscale/motion/fullpageAA/LIVEclaim.

Rootcommand:node <QA>/audit-SDE3-READINESS.cjs <isolatedorigin>.
Expectedcollection72/scopedprotectedcomparatorexit0. Observationfindings>0
means READ_COMPLETE_UI_DEFECT_OPEN, not ACCEPTED. Harnesserrors failcollection.
No paidproviders/payment actions. PROVIDER_CALLS_APP=0/WALLET_MUTATIONS=0/
PRODUCTION_DATA_MUTATIONS=0/DEPLOY=NO/LIVE_PASS=NOT_TESTED.
