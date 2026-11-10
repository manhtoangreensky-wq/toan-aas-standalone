import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../static/portal/portal.js',import.meta.url),'utf8');
const saved={product:'Original customer product',message:'Original customer message',message_mode:'provided',message_theme:'memory',style:'cinematic',language:'en',idea_choice:1,motion_choice:2,video_duration_variant:5,music_choice:'none'};
const noop=()=>{};
const document={readyState:'loading',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{lang:'en',getAttribute:()=>null,setAttribute:noop,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
const window={document,navigator:{language:'en'},location:{pathname:'/video-studio/cinematic-concept',search:'',href:'http://unit.invalid/video-studio/cinematic-concept',origin:'http://unit.invalid'},addEventListener:noop,dispatchEvent:noop,matchMedia:()=>({matches:false}),localStorage:{getItem:()=>null,setItem:noop},__TOAN_AAS_PORTAL__:{path:'/video-studio/cinematic-concept',cinematicConceptSaveSource:saved}};
const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout:noop,clearTimeout:noop});
const anchor='  window.TOANAASPortal = Object.freeze({';
vm.runInContext(source.replace(anchor,'  window.__cinematicFormCheck={cinematicConceptFormMatchesSavedSource,normalizeCinematicConceptPlanSaveSource};\n'+anchor),sandbox);
function form(overrides={},action='cinematic-concept-compose'){
 const values={...Object.fromEntries(Object.entries(saved).map(([k,v])=>[k,String(v)])),...overrides};
 return{getAttribute:()=>action,querySelectorAll:()=>Object.entries(values).map(([name,value])=>({name,value,type:'select-one'}))};
}
test('valid unchanged native string choices keep the actual cinematic form current',()=>assert.equal(window.__cinematicFormCheck.cinematicConceptFormMatchesSavedSource(form()),true));
for(const[name,value]of[['product','Changed product'],['message','Changed message'],['idea_choice','2'],['motion_choice','1'],['video_duration_variant','10'],['language','vi']]){
 test('changed '+name+' still makes the actual cinematic form stale',()=>assert.equal(window.__cinematicFormCheck.cinematicConceptFormMatchesSavedSource(form({[name]:value})),false));
}
for(const key of['idea_choice','motion_choice','video_duration_variant'])for(const value of['','01','1e0','1.0',' 1','NaN','999999999999999999999']){
 test('invalid '+key+' '+JSON.stringify(value)+' cannot become current',()=>assert.equal(window.__cinematicFormCheck.cinematicConceptFormMatchesSavedSource(form({[key]:value})),false));
}
test('wrong form action cannot inherit cinematic save freshness',()=>assert.equal(window.__cinematicFormCheck.cinematicConceptFormMatchesSavedSource(form({},'other-compose')),false));
test('transport normalizer still rejects all-numeric string payloads',()=>{
 const fields=Object.fromEntries(Object.entries(saved).map(([k,v])=>[k,String(v)]));
 assert.deepEqual(Object.keys(window.__cinematicFormCheck.normalizeCinematicConceptPlanSaveSource(fields)),[]);
});
