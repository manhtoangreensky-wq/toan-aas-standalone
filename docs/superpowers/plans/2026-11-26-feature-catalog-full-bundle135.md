# FBC135 — kế hoạch đồng bộ bộ chữ đầy đủ

BASEfdfe2f75,Issue689,PR814đãgiao. Speccùngngàyfull-bundle135.
Mỗi bước cơ học2–5phút;gatesphức tạp giữ chung và chạy tuần tự.

1. Khóa810acceptedworker values từproposalđãcó,khônggọi lại3worker.
   Fixturecanonical tham chiếuCD108.copy/hash;fulli18n beforea342ad11.
   Tạo recordthêm39mục/3locale vàđổi286desc,giữ290valuesđãđúng.
   Đo actualrecordcount/afterhash,không dự đoán bằng tên task.
2. Primarytest thực thiAPIi18nthật vàmoduleCard thật. RED trênBASE,
   khôngmissingimport/setup error. Non-catalog/unknownfallback và
   workspace_menu branch riêng phải giữ. Destination-pagecopy giữ nguyên
   ngoại trừ mô tả `/documents` dùng entry-key chung đã ghi rõ trong spec.
   Kiểm actual localizedPageDescription ở VI/EN/ZH: BASE RED/current GREEN;
   không đổi app data/hash và không tính thiếu sót spec là worker failure.
3. Tích hợp dữ liệu cơ học từrecordset đãkhóa;source bằngBASE+records.
4. Pressuretrướchelper:sourceandsnapshot exactinverse,idempotent,
   OLD/unrelatedpass,unknownbytes/entryidentity/ordergiữ,partial/
   changed/duplicate/detached/reorderedfail. Nối trướcNLR;typeguard
   cũ đi trướcsnapshotleaf. Haioldtestsghiđúnghistorical/giữexpectations.
5. GREEN mới+consumerảnhhưởng mộtlượt. Chỉruncafail/nhómbịảnhhưởng
   khirootQA phải sửa;khônggọi lỗicoordinatorlàworkerfailure.
6. BrowserHTTPfulli18n+actualmoduleCard/realSVGicon/CSS/customerShell,
   native810/href/Tab/375/1440/sángtối;đo contrast/focus/targets/
   overflow;không thayCSS vìkhungQAsai. Noauth/API/providercalls.
7. Groupedreview/docsops/comparison/ninecases/Tester/metadata/manifest.
   Source+protected+secretgates phảiREADYtrướccommit/push.
8. Web-onlyprovenance/verify,mộtPR,CIexactHEADhaiSUCCESS,mergepin/
   treeexact,exclusiveWebdeploy,runtime/7+7assets/2receiptreadback.

CI45872549883 phát hiện một raw Composer historical pin không đi qua
import closure đã chạy. Phụ lục7200174365 trước sửa đúng một QA reader,
giữ expected hashes/records/fixtures và rawFBCacceptance. RED1fail/0error,
GREEN nhóm liên quan19PASS/exit0; chỉ push correction vào cùng PR815,
không appchange/workerfail hoặc merge run lỗi.

10statescósẵn giữ;khôngđọccampaignstate,khôngcleanup lanman.
Signedproductionkhông cóphiênđăngnhậphiệnhành:khôngloginmới,
ghiNOT_TESTED,tiếptụcnhữngphầngoalkhôngbịảnhhưởng. Motioncuối.
