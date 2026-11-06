import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild,strategyContext,strategyId,customerProfile} from './helpers/publishing-child-render.mjs';

const viForeign=/\b(?:Web|Portal|Creators|Core Bridge|audience|brand|guardrails|direction|content|Affiliate|Website|follow|lead|inbox|feed|Claim|CSRF|URL|profile_created|profile_updated|profile_archived|profile_restored|strategy_previewed|unknown_event)\b/i;
const viLeak=/[À-ỹĐđ]|Ví dụ|Ngăn cách|Chọn nhịp|Khôi phục|Không affiliate/;

for(const locale of ['vi','en','zh']){
  for(const state of ['guarded','empty','library','detail','archived','missing']){
    test(`${locale}: Channel Strategy ${state} fixed copy and hints follow interface language`,()=>{
      const detail=['detail','archived','missing'].includes(state);
      const route=detail?'/content/channel-strategy/'+strategyId:'/content/channel-strategy';
      const r=renderChild(locale,route,strategyContext(state));
      const rendered=r.text+' '+r.attributes;
      // “Trang web” is the localized platform noun; bare English Web remains forbidden.
      if(locale==='vi')assert.doesNotMatch(rendered.replace(/\btrang web\b/gi,''),viForeign);
      else assert.doesNotMatch(rendered,viLeak);
      if(locale==='zh')assert.doesNotMatch(rendered,/\b(?:Web|Portal|Creators|Core Bridge|Affiliate|Website|follow|lead|inbox|feed|Claim|CSRF|URL|Bot)\b/i);
      assert.doesNotMatch(rendered,/profile (?:created|updated|archived|restored)|strategy previewed|unknown event/);
    });
  }
  test(`${locale}: Channel Strategy retains saved option values and customer records`,()=>{
    const r=renderChild(locale,'/content/channel-strategy',strategyContext());
    for(const name of ['platform','primary_goal','preferred_aspect_ratio']){
      const f=r.fields.find(f=>f.name===name);
      assert.ok(f);
      const values=Array.from(f.options,([value])=>value);
      assert.deepEqual(values,name==='platform'?['tiktok','facebook','instagram','youtube','website','other']:name==='primary_goal'?['content','authority','community','follow','lead','sales','website']:['9:16','16:9','1:1','4:5']);
      if(name==='platform')assert.equal(Array.from(f.options).find(([value])=>value==='website')[1],{vi:'Trang web',en:'Website',zh:'网站'}[locale]);
    }
    assert.ok(r.text.includes('CUSTOMER_CHANNEL'));
    assert.match(r.html,/data-portal-action="channel-strategy-create"/);
    assert.match(r.html,/data-portal-action="channel-strategy-filter"/);
    assert.match(r.html,new RegExp('href="/content/channel-strategy/'+strategyId+'"'));
  });
  test(`${locale}: the disabled affiliate-policy label is localized without changing the flag`,()=>{
    const context=strategyContext();
    context.channelStrategyProfiles=[{...customerProfile(),affiliate_allowed:false}];
    const r=renderChild(locale,'/content/channel-strategy',context);
    assert.ok(r.text.includes({vi:'Không dùng tiếp thị liên kết',en:'No affiliate marketing',zh:'不使用联盟营销'}[locale]),r.text);
    assert.equal(context.channelStrategyProfiles[0].affiliate_allowed,false);
  });
}

test('Channel Strategy revisions retain the existing integer range without a missing cross-bundle helper',()=>{
  const {validateStrategyRevision}=renderChild('vi','/content/channel-strategy',strategyContext('guarded'));
  for(const [input,expected] of [[1,1],['2',2],[1000000,1000000],[0,0],[-1,0],[1.5,0],[1000001,0],['bad',0],[null,0],[undefined,0]]){
    assert.equal(validateStrategyRevision(input),expected,String(input));
  }
});

test('the channel library and its detail keep the same Publishing mobile destination',()=>{
  const {mobileGroupForPath}=renderChild('vi','/content/channel-strategy',strategyContext('guarded'));
  assert.equal(mobileGroupForPath('/content/channel-strategy'),'publishing');
  assert.equal(mobileGroupForPath('/content/channel-strategy/'+strategyId),'publishing');
});

test('channel navigation does not change other mobile destinations or expose admin routes',()=>{
  const {mobileGroupForPath}=renderChild('vi','/content/channel-strategy',strategyContext('guarded'));
  for(const [path,expected]of [['/studio','studio'],['/projects','projects'],['/wallet','wallet'],['/account','account'],['/admin',null],['/admin/support',null]])assert.equal(mobileGroupForPath(path),expected,path);
});
