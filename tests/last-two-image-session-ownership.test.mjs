import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const integration=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const specs=[['imageMotionPlanner','image-motion-planner','imageMotionPlannerComposeRequestEpoch','imageMotionPlannerSaveRequestEpoch','imageMotionPlannerSessionEpoch','imageMotionPlannerSessionToken','imageMotionPlannerRequestIsCurrent']];
function runtime(spec){
 const[key,route,compose,save,epoch,stamp,helper]=spec,noop=()=>{};
 const state={path:'/video-studio/'+route,account:{role:'user'},session:{authenticated:true,csrfToken:'qa-signed-current-stamp'},[key+'Enabled']:true};
 const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
 const window={__TOAN_AAS_PORTAL__:state,document,TOANAASPortal:{mount:noop},navigator:{language:'vi'},location:{pathname:state.path,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+state.path},addEventListener:noop,dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop,fetch:()=>{throw Error('Network forbidden');}});
 const end=integration.lastIndexOf('}());');assert.ok(end>0);
 const expose=`window.__ownership={current:${helper},seed(value){${compose}=1;${save}=1;${epoch}=1;if(typeof ${stamp}!=='undefined')${stamp}=value;}};\n`;
 vm.runInContext(integration.slice(0,end)+expose+integration.slice(end),sandbox);window.__ownership.seed('qa-signed-current-stamp');
 return{state,window,check:(kind='compose',request=1,session=1,token='qa-signed-current-stamp',path=state.path)=>window.__ownership.current(kind,request,session,token,path)};
}
for(const spec of specs){const[key,route]=spec;
 test(route+': current owned signed response works without publishing internal account ID',()=>{const app=runtime(spec);assert.equal(Object.hasOwn(app.state.account,'id'),false);assert.equal(app.check(),true);assert.equal(app.check('save'),true);});
 test(route+': missing captured session stamp stays rejected',()=>assert.equal(runtime(spec).check('compose',1,1,''),false));
 test(route+': old captured stamp stays rejected after signed session changes',()=>{const app=runtime(spec);app.window.__ownership.seed('qa-new-signed-session');assert.equal(app.check(),false);});
 test(route+': cleared private stamp stays rejected',()=>{const app=runtime(spec);app.window.__ownership.seed('');assert.equal(app.check(),false);});
 test(route+': older request epoch stays rejected',()=>assert.equal(runtime(spec).check('compose',0),false));
 test(route+': older hydration/session epoch stays rejected',()=>assert.equal(runtime(spec).check('compose',1,0),false));
 test(route+': wrong captured route stays rejected',()=>assert.equal(runtime(spec).check('compose',1,1,'qa-signed-current-stamp','/video-studio/other'),false));
 test(route+': current navigation away stays rejected',()=>{const app=runtime(spec);app.window.location.pathname='/studio';app.state.path='/studio';assert.equal(app.check('compose',1,1,'qa-signed-current-stamp','/video-studio/'+route),false);});
 test(route+': disabled route stays rejected',()=>{const app=runtime(spec);app.state[key+'Enabled']=false;assert.equal(app.check(),false);});
 test(route+': unsigned current state stays rejected',()=>{const app=runtime(spec);app.state.session.authenticated=false;assert.equal(app.check(),false);});
}
