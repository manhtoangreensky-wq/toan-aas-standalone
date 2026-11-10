import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=process.env.WEBAPP_SOURCE_ROOT||path.resolve(here,'..');
const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
const formSelector='form[data-portal-action="creative-motion-guide-compose"]';
const hintAttribute='data-creative-motion-guide-selected-name';
const names=['topic_kind','language','style'];
const longLabels=['Công cụ trí tuệ nhân tạo / phần mềm','Tiếng Trung giản thể','Nội dung người dùng đời thường'];

function runtime({raf=true,canvas=true,wrongForm=false}={}){
  const geometry=[],frames=[],timers=[],listeners=new Map(),fontCallbacks=[];
  const noop=()=>{};
  const datasetKey=value=>value.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
  function element(tag='span'){
    let text='';
    const node={
      tagName:tag.toUpperCase(),attributes:{},dataset:{},children:[],parentElement:null,
      className:'',isConnected:true,hidden:false,style:{},
      setAttribute(name,value){geometry.push('write:attr');this.attributes[name]=String(value);if(name.startsWith('data-'))this.dataset[datasetKey(name.slice(5))]=String(value);},
      getAttribute(name){return this.attributes[name]??(name.startsWith('data-')?this.dataset[datasetKey(name.slice(5))]:null)??null;},
      hasAttribute(name){return this.getAttribute(name)!==null;},
      removeAttribute(name){geometry.push('write:remove-attr');delete this.attributes[name];if(name.startsWith('data-'))delete this.dataset[datasetKey(name.slice(5))];},
      appendChild(child){geometry.push('write:append');if(child.parentElement)child.remove();this.children.push(child);child.parentElement=this;child.isConnected=this.isConnected;return child;},
      insertBefore(child,before){geometry.push('write:insert');if(child.parentElement)child.remove();const at=this.children.indexOf(before);if(at<0)this.children.push(child);else this.children.splice(at,0,child);child.parentElement=this;child.isConnected=this.isConnected;return child;},
      insertAdjacentElement(where,child){assert.equal(where,'afterend');this.after(child);},
      after(child){assert.ok(this.parentElement);const parent=this.parentElement,index=parent.children.indexOf(this);parent.insertBefore(child,parent.children[index+1]||null);},
      remove(){geometry.push('write:remove');if(this.parentElement){const siblings=this.parentElement.children,index=siblings.indexOf(this);if(index>=0)siblings.splice(index,1);}this.parentElement=null;this.isConnected=false;},
      querySelectorAll(selector){
        const descendants=this.children.flatMap(child=>[child,...child.querySelectorAll('*')]);
        if(selector==='*')return descendants;
        if(selector.includes(hintAttribute)){
          const match=selector.match(/data-creative-motion-guide-selected-name=["']?([^"'\]]+)/);
          return descendants.filter(child=>child.hasAttribute(hintAttribute)&&(!match||child.getAttribute(hintAttribute)===match[1]));
        }
        if(/(^|[,\s])select\b/.test(selector))return descendants.filter(child=>child.tagName==='SELECT');
        return [];
      },
      querySelector(selector){return this.querySelectorAll(selector)[0]||null;},
      closest(selector){if(selector.includes('portal-field')||selector==='label')return this.parentElement;return null;},
      getBoundingClientRect(){geometry.push('read:rect');return {width:this.clientWidth||220,height:44,left:0,right:this.clientWidth||220,top:0,bottom:44};}
    };
    Object.defineProperty(node,'textContent',{get:()=>text,set:value=>{geometry.push('write:text');text=String(value);}});
    Object.defineProperty(node,'innerHTML',{get:()=>'',set:()=>{throw Error('Selected name must use textContent, never innerHTML');}});
    Object.defineProperty(node,'nextElementSibling',{get(){const siblings=this.parentElement?.children||[],index=siblings.indexOf(this);return siblings[index+1]||null;}});
    return node;
  }
  function makeForm(labels=longLabels){
    const form=element('form');form.attributes['data-portal-action']=wrongForm?'other-action':'creative-motion-guide-compose';
    form.fields=names.map((name,index)=>{
      const field=element('label'),select=element('select');field.className='portal-field';form.appendChild(field);field.appendChild(select);
      select.name=name;select.value='value-'+name;select.disabled=index===2;select.selectedIndex=0;
      select.attributes.name=name;
      let width=130;
      Object.defineProperty(select,'clientWidth',{get:()=>{geometry.push('read:client');return width;},set:value=>{width=value;}});
      select.options=[{value:select.value,text:labels[index],label:labels[index],textContent:labels[index]}];
      Object.defineProperty(select,'selectedOptions',{get(){return this.selectedIndex>=0?[this.options[this.selectedIndex]]:[];}});
      Object.defineProperty(select,'offsetWidth',{get:()=>select.clientWidth});
      return {field,select};
    });
    return form;
  }
  let currentForm=makeForm();
  const initialForm=currentForm;
  function formIsCurrent(){return currentForm&&currentForm.isConnected&&currentForm.getAttribute('data-portal-action')==='creative-motion-guide-compose';}
  const document={
    readyState:'loading',title:'',addEventListener:noop,
    querySelector(selector){if(selector===formSelector||selector.includes('form[')&&selector.includes('creative-motion-guide-compose'))return formIsCurrent()?currentForm:null;return null;},
    querySelectorAll(selector){if(selector.includes(hintAttribute))return formIsCurrent()?currentForm.querySelectorAll(selector):[];return [];},
    getElementById:()=>null,
    createElement(tag){if(tag==='canvas')return {getContext(){return canvas?{font:'',measureText(value){geometry.push('read:measure');return {width:String(value).length*8};}}:null;}};return element(tag);},
    documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},
    body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop},
    fonts:{ready:{then(callback){fontCallbacks.push(callback);return {catch:noop};}}}
  };
  const computedStyle=select=>{
    geometry.push('read:style');
    return {font:'16px Arial',fontSize:'16px',fontFamily:'Arial',fontWeight:'400',fontStyle:'normal',paddingLeft:'8px',paddingRight:'8px',borderLeftWidth:'1px',borderRightWidth:'1px',getPropertyValue(key){return {'font':'16px Arial','font-size':'16px','padding-left':'8px','padding-right':'8px'}[key]||'';}};
  };
  const window={
    document,navigator:{language:'vi'},location:{pathname:'/video-studio/motion-guide',search:'',href:'https://unit.invalid/video-studio/motion-guide',origin:'https://unit.invalid'},
    addEventListener(name,handler){if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(handler);},
    dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),
    localStorage:{getItem:()=>null,setItem:noop},getComputedStyle:computedStyle,
    setTimeout(callback){timers.push(callback);return timers.length;},clearTimeout:noop
  };
  if(raf)window.requestAnimationFrame=callback=>{frames.push(callback);return frames.length;};
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,
    getComputedStyle:computedStyle,setTimeout:window.setTimeout,clearTimeout:noop,
    requestAnimationFrame:window.requestAnimationFrame,fetch:()=>{throw Error('Network forbidden in selected-name tests');}});
  vm.runInContext(i18n,sandbox);
  const anchor='  window.TOANAASPortal = Object.freeze({';
  assert.ok(portal.includes(anchor));
  vm.runInContext(portal.replace(anchor,'  window.__selectedNamesTest={schedule:typeof scheduleCreativeMotionGuideSelectedNames==="function"?scheduleCreativeMotionGuideSelectedNames:null,synchronize:synchronizeCreativeMotionGuideForm,bind:bindInteractions};\n'+anchor),sandbox);
  geometry.length=0;
  const schedule=()=>{assert.equal(typeof window.__selectedNamesTest.schedule,'function','Private selected-name scheduler is missing');window.__selectedNamesTest.schedule();};
  const flush=()=>{
    let count=0;
    while(frames.length||timers.length){if(++count>20)throw Error('Unbounded selected-name scheduling');const callback=frames.length?frames.shift():timers.shift();callback();}
  };
  const hints=form=>(form||currentForm)?.querySelectorAll('['+hintAttribute+']')||[];
  const replace=(next=true)=>{
    if(currentForm){currentForm.isConnected=false;for(const {select,field} of currentForm.fields){select.isConnected=false;field.isConnected=false;}}
    currentForm=next?makeForm():null;
    geometry.length=0;
    return currentForm;
  };
  return {schedule,flush,hints,geometry,frames,listeners,fontCallbacks,initialForm,makeForm,replace,synchronize:()=>window.__selectedNamesTest.synchronize(currentForm),bind:()=>window.__selectedNamesTest.bind(),
    get form(){return currentForm;},window,
    fireResize(){for(const handler of listeners.get('resize')||[])handler({type:'resize'});},
    settleFonts(){for(const callback of fontCallbacks)callback();}
  };
}
function states(form){return form.fields.map(({select})=>({name:select.name,value:select.value,selectedIndex:select.selectedIndex,disabled:select.disabled,attributes:{...select.attributes},optionText:select.options.map(option=>option.textContent),optionValues:select.options.map(option=>option.value)}));}
function assertHints(app,expectedNames=names){
  const hints=app.hints();assert.equal(hints.length,expectedNames.length,'Only clipped select values receive a line');
  for(const name of expectedNames){
    const {select}=app.form.fields.find(item=>item.select.name===name);
    const matches=hints.filter(hint=>hint.getAttribute(hintAttribute)===name);
    assert.equal(matches.length,1,'There must be one line per clipped select');
    assert.equal(matches[0].getAttribute('aria-hidden'),'true','Native selected value is already accessible');
    assert.equal(matches[0].textContent,select.options[select.selectedIndex].textContent);
    assert.equal(select.nextElementSibling,matches[0],'The full selected-name line belongs below its select');
  }
}

for(const name of names){
  test(name+': only the clipped selected label receives a full-name line and removes it when fitting',()=>{
    const app=runtime();
    for(const {select} of app.form.fields)select.clientWidth=1000;
    const target=app.form.fields.find(item=>item.select.name===name).select;target.clientWidth=100;
    const before=states(app.form);app.schedule();app.flush();assertHints(app,[name]);assert.deepEqual(states(app.form),before);
    target.clientWidth=1000;app.schedule();app.flush();assert.equal(app.hints().length,0,'Fitting fields leave no empty placeholder');
  });
}
test('all three clipped selectors show full labels without changing native values, options or disabled state',()=>{
  const app=runtime(),before=states(app.form);app.schedule();app.flush();assertHints(app);assert.deepEqual(states(app.form),before);
});
test('changing the selected value updates its sole text-only line without duplicate nodes',()=>{
  const app=runtime(),select=app.form.fields[2].select;app.schedule();app.flush();
  const next='Tên phong cách khác dài hơn chiều rộng có sẵn';
  select.options.push({value:'other',text:next,label:next,textContent:next});select.selectedIndex=1;select.value='other';
  app.schedule();app.schedule();app.flush();assertHints(app);assert.equal(app.hints().filter(h=>h.getAttribute(hintAttribute)==='style').length,1);
  select.options[1].textContent='Ngắn';select.options[1].text='Ngắn';select.options[1].label='Ngắn';
  app.schedule();app.flush();assertHints(app,['topic_kind','language']);
});
test('repeated scheduling coalesces to a single animation frame and does not duplicate hints',()=>{
  const app=runtime();app.schedule();app.schedule();app.schedule();assert.equal(app.frames.length,1);
  app.flush();assertHints(app);app.schedule();app.flush();assertHints(app);
});
test('all selector geometry is read before any selected-name DOM mutation',()=>{
  const app=runtime();app.schedule();app.flush();assertHints(app);
  const firstWrite=app.geometry.findIndex(value=>value.startsWith('write:'));
  assert.ok(firstWrite>=0);
  assert.equal(app.geometry.slice(firstWrite).some(value=>value.startsWith('read:')),false,
    'Geometry reads after hint writes can cause repeated layout work');
});
test('a queued callback queries the current replacement form rather than retaining detached selectors',()=>{
  const app=runtime(),old=app.form;app.schedule();app.replace();app.flush();assertHints(app);assert.equal(app.hints(old).length,0);
});
test('leaving the motion route before the queued callback does not write to a detached form',()=>{
  const app=runtime(),old=app.form;app.schedule();app.window.location.pathname='/dashboard';app.replace(false);app.flush();assert.equal(app.hints(old).length,0);
  app.window.location.pathname='/video-studio/motion-guide';app.replace();app.schedule();app.flush();assertHints(app);
});
test('no current motion form is a safe no-op',()=>{
  const app=runtime();app.replace(false);app.schedule();assert.doesNotThrow(()=>app.flush());assert.equal(app.hints().length,0);
});
test('a different form action receives no selected-name lines',()=>{
  const app=runtime({wrongForm:true});app.schedule();app.flush();assert.equal(app.hints().length,0);
});
test('missing requestAnimationFrame does not crash or change native values',()=>{
  const app=runtime({raf:false}),before=states(app.form);assert.doesNotThrow(()=>{app.schedule();app.flush();});assert.deepEqual(states(app.form),before);assert.equal(app.hints().length,0);
});
test('unavailable canvas measurement does not crash or change native values',()=>{
  const app=runtime({canvas:false}),before=states(app.form);assert.doesNotThrow(()=>{app.schedule();app.flush();});assert.deepEqual(states(app.form),before);assert.equal(app.hints().length,0);
});
test('selected label markup stays plain text instead of becoming HTML',()=>{
  const app=runtime(),value='<img src=x onerror=alert(1)> nguyên văn dài';
  app.form.fields[0].select.options[0]={value:'value-topic_kind',text:value,label:value,textContent:value};
  app.schedule();app.flush();const hint=app.hints().find(node=>node.getAttribute(hintAttribute)==='topic_kind');
  assert.ok(hint);assert.equal(hint.textContent,value);assert.equal(hint.children.length,0);
});
test('resize re-evaluates fitting labels without retaining a placeholder',()=>{
  // Production mount calls bindInteractions. This loading-state VM deliberately
  // avoids mount, so execute that same binder before exercising its listeners.
  const app=runtime();app.bind();app.schedule();app.flush();assertHints(app);
  for(const {select} of app.form.fields)select.clientWidth=1000;
  app.fireResize();app.flush();assert.equal(app.hints().length,0);
});
test('font readiness re-evaluates clipped selected labels',()=>{
  const app=runtime();app.bind();app.settleFonts();app.flush();assertHints(app);
});
test('a queued callback on a different route does not mutate even a still-connected old form',()=>{
  const app=runtime();app.schedule();app.window.location.pathname='/dashboard';app.flush();assert.equal(app.hints().length,0);
});
test('selectors with no selected option leave no full-name placeholder',()=>{
  const app=runtime();for(const {select} of app.form.fields)select.selectedIndex=-1;
  app.schedule();app.flush();assert.equal(app.hints().length,0);
});
test('a label exactly equal to the padding and one-em reserved budget counts as fitting',()=>{
  const app=runtime();for(const {select} of app.form.fields)select.clientWidth=select.options[0].textContent.length*8+8+8+16;
  app.schedule();app.flush();assert.equal(app.hints().length,0);
});
test('the existing motion form synchronization schedules the selected-name refresh',()=>{
  const app=runtime();app.synchronize();app.flush();assertHints(app);
});
