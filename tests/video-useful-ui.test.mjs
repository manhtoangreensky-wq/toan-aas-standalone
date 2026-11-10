import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const specs=[['prompt-planner','video-prompt-plan',15],['idea-planner','video-idea-planner-compose',12],['self-shot-planner','self-shot-scene-planner-compose',17]];
for(const[route,action,count]of specs){
 const raw={capabilities:{[action]:true,'video-plan-create':true},pageStates:{['/video-studio/'+route]:'ready'}},view=renderChild('vi','/video-studio/'+route,raw);
 test(route+': remove narrative/metrics/execution blocks without replacing them by blank cards',()=>{
  assert.equal(view.html.includes('portal-video-prompt-planner-intro'),false);
  assert.equal(view.html.includes('portal-video-prompt-planner-boundary'),false);
  assert.equal(view.html.includes('portal-video-prompt-planner-guard-list'),false);
  assert.equal(view.html.includes('class="portal-video-prompt-planner-layout"'),false);
  assert.ok(view.html.includes('class="portal-stack"'));
 });
 test(route+': retain all existing real input/action/result controls',()=>{
  const form=view.html.match(new RegExp('<form\\b[^>]*data-portal-action="'+action+'"[\\s\\S]*?<\\/form>'))?.[0];
  assert.ok(form);assert.equal([...form.matchAll(/\bname="[^"]*"/g)].length,count);
  assert.ok(form.includes('data-portal-no-transient'));
  assert.equal(view.context.path,'/video-studio/'+route);
  assert.ok(view.html.includes('<h1')&&view.html.includes('portal-card-title'));
 });
}
