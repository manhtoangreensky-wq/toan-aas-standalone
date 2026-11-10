import assert from 'node:assert/strict';

const keys=['autopostHub.page.title','autopostHub.page.description','shellNav.autoPostHub'];
const before={
 vi:['Đăng bài tự động','Chuẩn bị nội dung, rà soát lịch và theo dõi phân phối đa kênh trong một không gian rõ ràng.','Đăng bài tự động'],
 en:['AutoPost Hub','Prepare content, review schedules and track multi-channel distribution in one clear workspace.','AutoPost Hub'],
 zh:['自动发布中心','在一个清晰的工作区中准备内容、审核日程并跟踪多渠道分发。','自动发布中心']
};
const approved={
 vi:['Đăng bài','Lập định hướng kênh, sắp xếp lịch nội dung và rà soát bài đăng.','Đăng bài'],
 en:['Publishing','Plan channel direction, organize content dates and review posts.','Publishing'],
 zh:['内容发布','规划渠道方向、安排内容日程并审核帖子。','内容发布']
};

// Compare every historical value while permitting only the three explicitly
// approved metadata changes and the two new customer-copy namespaces.
export function customerCopyHistoricalSnapshot(entries,locale){
 return entries.filter(([key])=>!key.startsWith('customerPublishingUi.')&&!key.startsWith('customerBridgeFeedback.')).map(([key,value])=>{
  const index=keys.indexOf(key);
  if(index<0)return[key,value];
  assert.equal(value,approved[locale][index],'only the reviewed publishing metadata may replace its historical value: '+key);
  return[key,before[locale][index]];
 });
}
