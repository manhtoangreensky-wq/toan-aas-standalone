"""Behavioral motion regressions, not a browser FPS/performance verdict.

Execute the production helper. The DOM boundary records layout reads, style
writes and scheduled callbacks; it cannot prove visual fidelity or live jank.
"""
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
function env(reduced = false) {
  const log = [], elements = [], raf = new Map(), timers = new Map(), observers = [];
  let nextId = 0;
  function el(name) {
    const attrs = new Map(), classes = new Set(), listeners = new Map(), styles = new Map();
    const e = {
      name, dataset: {}, listeners, styles, rect: {top: 1000, bottom: 1200, left: 0, width: 400, height: 200},
      classList: {add: (...xs) => xs.forEach(x => classes.add(x)), remove: (...xs) => xs.forEach(x => classes.delete(x)), contains: x => classes.has(x)},
      style: {setProperty(k,v) { log.push('write:' + name); styles.set(k,v); }, removeProperty(k) {styles.delete(k);}},
      setAttribute(k,v) {log.push('write-attribute:' + name); attrs.set(k,v);}, getAttribute: k => attrs.get(k) || null,
      removeAttribute(k) {attrs.delete(k);},
      addEventListener(k,f) {if (!listeners.has(k)) listeners.set(k,new Set()); listeners.get(k).add(f);},
      removeEventListener(k,f) {listeners.get(k)?.delete(f);},
      fire(k,event={}) {for (const f of [...(listeners.get(k)||[])]) f({currentTarget:e,...event});},
      getBoundingClientRect() {log.push('read:' + name); return e.rect;},
      querySelector: () => null, querySelectorAll: () => [], closest: () => null, matches: () => false
    };
    elements.push(e); return e;
  }
  const root = el('root'), header = el('header'), pointer = el('pointer'), hero = el('hero');
  hero.rect={top:0,bottom:500,left:0,width:400,height:500};
  const layers = [el('layer-a'),el('layer-b')];
  layers[0].rect={top:100,bottom:300,left:0,width:400,height:200};
  layers.forEach((e,i) => e.setAttribute('data-landing-layer',i ? 'workflow' : 'studios'));
  root.querySelector = s => s === '.portal-landing-header' ? header : s === '.portal-landing-hero' ? hero : null;
  root.querySelectorAll = s => s === '[data-landing-layer]' ? layers : s.startsWith('[data-landing-pointer]') ? [pointer] : [];
  const win = el('window'), media = el('media');
  Object.assign(win, {innerHeight:800, scrollY:0,
    matchMedia: q => Object.assign(media,{matches:q.includes('prefers-reduced') ? reduced : true}),
    requestAnimationFrame: f => {const id=++nextId; raf.set(id,f); return id;},
    cancelAnimationFrame: id => raf.delete(id),
    setTimeout: f => {const id=++nextId; timers.set(id,f); return id;},
    clearTimeout: id => timers.delete(id),
    IntersectionObserver: class {
      constructor(cb) {this.cb=cb; this.targets=new Set(); observers.push(this);}
      observe(e) {this.targets.add(e);} unobserve(e) {this.targets.delete(e);} disconnect() {this.targets.clear();}
    }
  });
  const html = el('html'); html.scrollHeight=4000; html.clientHeight=800;
  vm.runInNewContext(source,{window:win,document:{documentElement:html}});
  function flush() {const work=[...raf.entries()]; raf.clear(); work.forEach(([,f])=>f());}
  function residual() {return {raf:raf.size,timers:timers.size,listeners:elements.reduce((n,e)=>n+[...e.listeners.values()].reduce((a,s)=>a+s.size,0),0),observed:observers.reduce((n,o)=>n+o.targets.size,0)};}
  return {el,root,win,pointer,layers,log,raf,flush,observers,residual,motion:win.TOANAASPortalMotion};
}
const out={};
{
  const e=env(), scroller=e.el('workspace-scroller');
  Object.assign(scroller,{scrollTop:0,clientHeight:800,scrollHeight:4000});
  e.root.closest=s=>s==='.portal-workspace' ? scroller : null;
  e.motion.mountLanding(e.root); e.flush(); e.flush();
  out.nestedBefore=e.layers[0].styles.get('--landing-section-progress');
  scroller.scrollTop=800; e.layers[0].rect.top=-700;
  scroller.fire('scroll'); scroller.fire('scroll');
  out.nestedFrames=e.raf.size; e.flush();
  out.nestedProgress=e.root.styles.get('--landing-scroll-progress');
  out.nestedAfter=e.layers[0].styles.get('--landing-section-progress');
  e.motion.unmountLanding(); out.nestedResidual=e.residual();
}
{
  const e=env(); e.motion.mountLanding(e.root); e.flush(); e.flush(); e.log.length=0;
  e.win.scrollY=800; e.win.fire('scroll'); e.win.fire('scroll');
  out.scrollFrames=e.raf.size; e.flush(); out.scrollOrder=[...e.log];
  out.scrollProgress=e.root.styles.get('--landing-scroll-progress');
  out.layerProgress=e.layers.map(x=>x.styles.get('--landing-section-progress'));
  e.motion.unmountLanding();
}
{
  const e=env(); e.motion.mountLanding(e.root); e.flush(); e.flush();
  e.pointer.fire('pointermove',{clientX:100,clientY:100}); e.pointer.fire('pointerleave');
  out.framesAfterLeave=e.raf.size; e.flush();
  out.activeAfterLeave=e.pointer.classList.contains('is-pointer-active');
  e.pointer.fire('pointermove',{clientX:200,clientY:200}); e.motion.unmountLanding();
  out.framesAfterUnmount=e.raf.size;
}
{
  const e=env(); const section=e.el('workspace-section');
  e.root.querySelectorAll=s=>s.startsWith('.portal-feature-directory-controls') ? [section] : [];
  e.motion.mountWorkspace(e.root);
  section.rect={top:20,bottom:220,height:200};
  e.win.fire('scroll'); e.flush();
  out.sectionVisible=section.classList.contains('is-visible');
  e.log.length=0; e.win.fire('scroll'); e.flush();
  out.settledReads=e.log.filter(x=>x==='read:workspace-section').length;
  e.motion.unmountWorkspace(); out.workspaceResidual=e.residual();
}
{
  const e=env();
  for(let i=0;i<20;i++) {
    e.motion.mountLanding(e.root); e.win.fire('scroll');
    e.pointer.fire('pointermove',{clientX:10,clientY:10}); e.motion.unmountLanding();
  }
  out.twentyCycles=e.residual();
}
{
  const e=env(true); e.motion.mountLanding(e.root);
  out.reduced=e.root.getAttribute('data-landing-scroll-motion');
  e.motion.unmountLanding(); out.reducedResidual=e.residual();
}
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def observed():
    result = subprocess.run(
        ["node", "-e", HARNESS, str(ROOT / "static/portal/portal-motion.js")],
        capture_output=True, text=True, check=True, timeout=20,
    )
    return json.loads(result.stdout)


def test_scroll_batches_geometry_before_style_writes(observed):
    order = observed["scrollOrder"]
    first_write = next(i for i, item in enumerate(order) if item.startswith("write"))
    assert not any(item.startswith("read:") for item in order[first_write:]), order
    assert observed["scrollFrames"] == 1
    assert observed["scrollProgress"] == "0.2500"
    assert observed["layerProgress"] == ["0.6073", "0.0000"]


def test_nested_workspace_scroll_drives_landing_motion(observed):
    assert observed["nestedFrames"] == 1
    assert observed["nestedProgress"] == "0.2500"
    assert observed["nestedBefore"] != observed["nestedAfter"]
    assert observed["nestedResidual"] == dict(raf=0, timers=0, listeners=0, observed=0)


def test_pointer_leave_cannot_reactivate_from_queued_frame(observed):
    assert observed["framesAfterLeave"] == 0
    assert observed["activeAfterLeave"] is False
    assert observed["framesAfterUnmount"] == 0


def test_revealed_workspace_does_not_keep_reading_geometry(observed):
    assert observed["sectionVisible"] is True
    assert observed["settledReads"] == 0
    assert observed["workspaceResidual"] == dict(raf=0, timers=0, listeners=0, observed=0)


def test_twenty_landing_teardowns_cancel_all_scheduled_work(observed):
    assert observed["twentyCycles"] == dict(raf=0, timers=0, listeners=0, observed=0)


def test_reduced_motion_preserves_static_content_without_work(observed):
    assert observed["reduced"] == "static"
    assert observed["reducedResidual"] == dict(raf=0, timers=0, listeners=0, observed=0)
