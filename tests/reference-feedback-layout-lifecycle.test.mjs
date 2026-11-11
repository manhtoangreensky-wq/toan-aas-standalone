import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';

const portal=fs.readFileSync(new URL('../static/portal/portal.js',import.meta.url),'utf8');
const start=portal.indexOf('  let referenceFeedbackObserver = null;');
const end=portal.indexOf('  function mountPortal(override)',start);
assert.ok(start>=0&&end>start,'extract the actual private feedback lifecycle helper');
const actualHelper=portal.slice(start,end);

function setup({empty=false,overflow=false}={}){
  const events=[],observers=[];let created=0;
  function node(name,rect={top:0,bottom:100,height:100}){
    created++;const classes=new Set(),attributes=new Map(),values=new Map();
    return {name,children:[],parentElement:null,rect,hidden:false,appendCalls:0,scrollCalls:[],focusCalls:0,value:'',scrollHeight:100,clientHeight:100,
      classList:{toggle(key,on){if(on)classes.add(key);else classes.delete(key);},contains:key=>classes.has(key)},
      style:{setProperty:(key,value)=>values.set(key,value),getPropertyValue:key=>values.get(key)||'',removeProperty:key=>values.delete(key)},
      setAttribute:(key,value)=>attributes.set(key,String(value)),getAttribute:key=>attributes.get(key)??null,removeAttribute:key=>attributes.delete(key),
      getBoundingClientRect(){return this.rect;},
      appendChild(child){if(child.parentElement)child.parentElement.children.splice(child.parentElement.children.indexOf(child),1);child.parentElement=this;this.children.push(child);this.appendCalls++;return child;},
      contains(child){for(let current=child;current;current=current.parentElement)if(current===this)return true;return false;},
      querySelector(selector){return selector==='[data-portal-header]'?this.children.find(child=>child.name==='header')||null:null;},
      insertAdjacentElement(position,child){assert.equal(position,'afterend');const parent=this.parentElement;if(child.parentElement)child.parentElement.children.splice(child.parentElement.children.indexOf(child),1);child.parentElement=parent;parent.children.splice(parent.children.indexOf(this)+1,0,child);events.push('restore-existing-region');},
      scrollIntoView(options){this.scrollCalls.push(JSON.parse(JSON.stringify(options)));},focus(){this.focusCalls++;}
    };
  }
  const body=node('body'),shell=node('shell'),workspace=node('workspace'),header=node('header'),main=node('main',{top:100,bottom:600,height:500});
  const dock=node('dock',{top:600,bottom:656,height:56}),region=node('toast-region'),tail=node('tail'),control=node('control',{top:200,bottom:240,height:40}),outside=node('outside'),retry=node('retry',{top:250,bottom:290,height:40}),form=node('compose-form');
  body.appendChild(shell);body.appendChild(region);body.appendChild(tail);shell.appendChild(workspace);workspace.appendChild(header);workspace.appendChild(main);workspace.appendChild(dock);main.appendChild(control);
  main.appendChild(form);main.appendChild(retry);header.appendChild(outside);retry.disabled=false;
  main.querySelector=selector=>selector==='button[data-portal-action="reference-format-planner-save-plan"]'?retry:selector==='form[data-portal-action="reference-format-planner-compose"][aria-busy="true"]'&&form.getAttribute('aria-busy')==='true'?form:null;
  region.setAttribute('aria-live','polite');region.setAttribute('aria-atomic','true');region.textContent='';control.value='SYNTHETIC_SOURCE_VALUE';
  const message=empty?null:node('native-message');
  if(message){message.textContent='Existing native recovery message';message.setAttribute('role','alert');region.appendChild(message);}
  region.scrollHeight=overflow?250:100;region.clientHeight=100;region.appendCalls=0;workspace.appendCalls=0;
  const document={body,activeElement:null,querySelector:selector=>selector==='[data-portal-toast]'?region:null,createElement(){throw Error('lifecycle helper must never create replacement DOM');}};
  class ResizeObserverDouble{
    constructor(callback){this.callback=callback;this.active=true;this.targets=[];this.id=observers.length+1;observers.push(this);events.push('new-'+this.id);}
    observe(target){this.targets.push(target);}
    disconnect(){this.active=false;events.push('disconnect-'+this.id);}
    fire(){assert.equal(this.active,true,'only the live observer delivers geometry changes');this.callback();}
  }
  const context=vm.createContext({document,window:{ResizeObserver:ResizeObserverDouble}});
  vm.runInContext(actualHelper+'\nglobalThis.invoke=syncReferenceFeedbackLayout;',context);
  const invoke=(enabled=true)=>context.invoke(shell,main,dock,enabled);
  const aria=()=>({live:region.getAttribute('aria-live'),atomic:region.getAttribute('aria-atomic'),messageRole:message?.getAttribute('role'),message:message?.textContent});
  return{body,shell,workspace,header,main,dock,region,tail,control,outside,retry,form,message,document,events,observers,invoke,aria,created:()=>created};
}

test('existing native region moves once without cloning its message or changing ARIA',()=>{
  const f=setup(),before=f.aria(),count=f.created();f.invoke();f.invoke();
  assert.equal(f.region.parentElement,f.workspace);assert.equal(f.workspace.children.filter(node=>node===f.region).length,1);
  assert.equal(f.workspace.appendCalls,1);assert.equal(f.region.children[0],f.message);assert.equal(f.created(),count);assert.deepEqual(f.aria(),before);
});

test('empty feedback relocates only its existing region and creates no placeholder node',()=>{
  const f=setup({empty:true}),count=f.created();f.region.scrollHeight=0;f.region.clientHeight=0;f.invoke();
  assert.equal(f.created(),count);assert.deepEqual(f.region.children,[]);assert.equal(f.region.appendCalls,0);assert.equal(f.workspace.appendCalls,1);
  assert.equal(f.region.getAttribute('tabindex'),null);assert.equal(f.region.parentElement,f.workspace);
});

test('remount disconnects the old observer before creating one live replacement; exit disconnects it',()=>{
  const f=setup();f.invoke();const first=f.observers[0];f.invoke();
  assert.equal(first.active,false);assert.equal(f.observers.filter(observer=>observer.active).length,1);
  assert.ok(f.events.indexOf('disconnect-1')<f.events.indexOf('new-2'),'old callbacks must stop before remount observation starts');
  assert.deepEqual(f.observers[1].targets,[f.region,f.dock,f.header]);
  f.invoke(false);assert.equal(f.observers[1].active,false);assert.equal(f.observers.filter(observer=>observer.active).length,0);
  f.invoke(false);assert.equal(f.observers.length,2,'route exit must not construct observers');
});

test('real observer callback updates the actual dock-inset variable when dock geometry changes',()=>{
  const f=setup();f.invoke();const observer=f.observers[0],key='--portal-feedback-dock-inset';
  assert.equal(f.workspace.style.getPropertyValue(key),'56px');f.dock.rect={top:600,bottom:672,height:72};observer.fire();
  assert.equal(f.workspace.style.getPropertyValue(key),'72px');f.dock.hidden=true;observer.fire();assert.equal(f.workspace.style.getPropertyValue(key),'0px');
  f.dock.hidden=false;f.dock.rect={top:600,bottom:624,height:24};observer.fire();assert.equal(f.workspace.style.getPropertyValue(key),'24px');
});

test('clipped active source control scrolls nearest without focus stealing or input mutation',()=>{
  const f=setup();f.document.activeElement=f.control;f.control.rect={top:90,bottom:130,height:40};f.invoke();
  assert.deepEqual(f.control.scrollCalls,[{block:'nearest',inline:'nearest'}]);assert.equal(f.document.activeElement,f.control);
  assert.equal(f.control.focusCalls,0);assert.equal(f.control.value,'SYNTHETIC_SOURCE_VALUE');
  f.control.rect={top:570,bottom:610,height:40};f.observers[0].fire();assert.equal(f.control.scrollCalls.length,2);
  assert.deepEqual(f.control.scrollCalls[1],{block:'nearest',inline:'nearest'});assert.equal(f.control.value,'SYNTHETIC_SOURCE_VALUE');
});

test('visible or unrelated active controls are never scrolled or focused by layout updates',()=>{
  const f=setup();f.document.activeElement=f.control;f.invoke();assert.deepEqual(f.control.scrollCalls,[]);
  f.document.activeElement=f.outside;f.outside.rect={top:-40,bottom:-10,height:30};f.observers[0].fire();
  assert.deepEqual(f.outside.scrollCalls,[]);assert.equal(f.outside.focusCalls,0);assert.equal(f.control.focusCalls,0);assert.equal(f.document.activeElement,f.outside);
  f.document.activeElement=null;f.observers[0].fire();assert.deepEqual(f.control.scrollCalls,[]);
});

test('body focus after a disabled save uses the enabled clipped recovery retry only as a scroll anchor',()=>{
  const f=setup();f.document.activeElement=f.body;f.form.setAttribute('aria-busy','true');f.retry.rect={top:610,bottom:650,height:40};f.invoke();
  assert.deepEqual(f.retry.scrollCalls,[{block:'nearest',inline:'nearest'}]);assert.equal(f.document.activeElement,f.body);
  assert.equal(f.retry.focusCalls,0);assert.equal(f.body.focusCalls,0);assert.equal(f.control.value,'SYNTHETIC_SOURCE_VALUE');
});

test('recovery fallback does not scroll or steal focus from a header control, disabled retry, or idle form',()=>{
  for(const state of ['header-active','retry-disabled','not-recovering']){
    const f=setup();f.document.activeElement=state==='header-active'?f.outside:f.body;const active=f.document.activeElement;
    if(state!=='not-recovering')f.form.setAttribute('aria-busy','true');f.retry.disabled=state==='retry-disabled';f.retry.rect={top:610,bottom:650,height:40};f.invoke();
    assert.deepEqual(f.retry.scrollCalls,[],state);assert.equal(f.document.activeElement,active,state);assert.equal(f.retry.focusCalls,0,state);
    assert.equal(f.outside.focusCalls,0,state);assert.equal(f.control.value,'SYNTHETIC_SOURCE_VALUE',state);
  }
});

test('only actual long-feedback overflow makes the existing region keyboard-focusable',()=>{
  const f=setup(),before=f.aria();f.invoke();const observer=f.observers[0];assert.equal(f.region.getAttribute('tabindex'),null);
  f.region.clientHeight=200;f.region.scrollHeight=201;observer.fire();assert.equal(f.region.getAttribute('tabindex'),null,'one-pixel rounding is not overflow');
  f.region.scrollHeight=202;observer.fire();assert.equal(f.region.getAttribute('tabindex'),'0');
  f.region.clientHeight=260;observer.fire();assert.equal(f.region.getAttribute('tabindex'),null);assert.deepEqual(f.aria(),before);
});

test('route exit restores the same shell-sibling region and removes every scoped layout affordance',()=>{
  const f=setup({overflow:true}),before=f.aria(),originalSiblings=[...f.body.children];f.invoke();
  assert.equal(f.shell.classList.contains('portal-shell--reference-feedback'),true);assert.equal(f.region.getAttribute('tabindex'),'0');
  f.invoke(false);assert.deepEqual(f.body.children,originalSiblings);assert.equal(f.region.parentElement,f.body);
  assert.equal(f.body.children[f.body.children.indexOf(f.shell)+1],f.region);assert.equal(f.workspace.children.includes(f.region),false);
  assert.equal(f.shell.classList.contains('portal-shell--reference-feedback'),false);assert.equal(f.workspace.style.getPropertyValue('--portal-feedback-dock-inset'),'');
  assert.equal(f.region.getAttribute('tabindex'),null);assert.deepEqual(f.aria(),before);assert.equal(f.region.children[0],f.message);
  assert.equal(f.observers.filter(observer=>observer.active).length,0);assert.equal(f.control.value,'SYNTHETIC_SOURCE_VALUE');
});
