# Tester session AP195-WRITE-CURRENTNESS-20261107

STATUS=LOCAL_ACCEPTED_PENDING_EXACT_HEAD_CI_DEPLOY_AND_SIGNED_LIVE
BASE_SHA=81374e73bcedbb1541c36a1cd79706dae55c5dc2
CASE_IDS=AP195-WRITE-01,AP195-WRITE-02,AP195-WRITE-03
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md

Actual full-integration baseline:48tests,16passed/32failed. After first worker
patch:48/48passed, zero skips/cancellations; indexed Node1,718/1,718 across197files.
Native2/2passed including three original temporary-DB write envelopes passed
through complete client handlers. CSRF403, idempotent replay, revision and signed
cross-account rejection are asserted. No session/CSRF token is forwarded to Node.

Browser12/12 normal form clicks at360/1440, create/edit/Approvals status, current
and switched-account responses. Actual form busy before ACK, current receipt/
redirect and stale no-effect assertions passed;12PNG files validated; page/console/
external/unknown errors0. Browser uses synthetic bootstrap/API, reduced motion,
and disables initial auth hydration only in served QA bytes: not signed LIVE.
An initial browser fixture incorrectly put a draft record into Approvals (which
only shows review records); all4setup failures were retained separately and the
fixture corrected, without application changes. Final12/12 is a full rerun.

Independent source review C0/I0/M1. Minor fake-control route mismatch on Approvals
corrected in QA and busy assertions rerun; app patch unchanged.14protected helpers
remain byte-identical. Existing native ownership test has one stale English
Calendar-title assertion; recorded as baseline, not skipped or weakened. New
native test checks ownership independently without asserting obsolete UI copy.

No API/backend/auth/CSRF authority/schema/ENV/provider/wallet/Bot/motion change.
Server writes are not aborted or retried. No broad translation or malformed-ACK
validation was included; full Campaign locale and signed production UI stay open.
Provider calls,wallet and production data mutations0. CI/artifact/runtime separate.

Tester metadata:32passed/1known Windows POSIX private-file-mode baseline failure
(0666 versus0600). Hash/byte/line metadata passed; no assertion weakening or skip.
Linux critical CI remains a required gate before merge.
