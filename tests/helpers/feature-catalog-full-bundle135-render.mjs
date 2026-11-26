import assert from "node:assert/strict";
import vm from "node:vm";

export function fullBundleI18n(source,locale="vi"){
  const document={title:"",documentElement:{lang:"",setAttribute(){}}};
  const window={document,navigator:{language:locale},dispatchEvent(){},CustomEvent:function(){}};
  vm.runInNewContext(source,{window,document,Intl,Date,Number,String,Object,Array,Set,Map,Math,RegExp});
  const api=window.TOANAASI18n;assert(api&&typeof api.t==="function");
  api.setLocale(locale,{emit:false});return api;
}

export function fullBundleConsumerSource(portal){
  const block=(start,end)=>{
    const at=portal.indexOf(start),to=portal.indexOf(end,at+start.length);
    assert(at>=0&&to>at,start);return portal.slice(at,to);
  };
  const declarations=["CATALOG_ENGINE_MODES","CATALOG_ENGINE_STATES","CATALOG_READINESS_STATES"].map(name=>{
    const row=portal.match(new RegExp("^  const "+name+" = new Set\\([^\\n]+\\);","m"));
    assert(row,name);return row[0];
  }).join("\n");
  return[
    block("const ICONS = Object.freeze(","\n  function portalBrandMark("),
    block("function portalI18n(","\n  // Public access copy"),
    block("function featureCatalogText(","\n  // Media Studio"),
    block("function safeText(","\n  function normalizePath("),
    block("function normalizePath(","\n  const CAPABILITY_HUB_FAMILY_KEYS"),
    block("function safeCatalogRoute(","\n  function catalogEntryRoute("),
    declarations,
    block("function normalizeCatalogEngine(","\n  function catalogEntryState("),
    block("function badge(","\n  function subtitleAssetOperationsReadBadge("),
    block("function displayPageTitle(","\n  function documentTitle("),
    block("function localizedPageDescription(","\n  function initials("),
    block("function moduleCard(","\n  function fallbackCatalogGroup(")
  ].join("\n");
}

export function fullBundleConsumer(portal,api,entries){
  const manifest=Object.fromEntries(entries.map(entry=>[entry.route,{
    path:entry.route,routePath:entry.route,title:"Owner page <safe>",description:"Owner page description & details",
    access:"member",status:"guarded",icon:"◩"
  }]));
  const window={TOANAASI18n:api,location:{pathname:"/features/video"}};
  const context=vm.createContext({
    window,manifest,Set,Object,Array,String,Number,
    ALLOWED_STATES:new Set(["ready","guarded","read_only"]),
    catalogEntryState(){throw Error("Fixture must supply a declared display state");},
    featureFamilyForPath:()=>null,ADMIN_DATA_VIEW_ROUTE_KEYS:{},ADMIN_ERP_ROUTE_I18N:{}
  });
  vm.runInContext(fullBundleConsumerSource(portal)+"\nglobalThis.__fbcRender = moduleCard;\nglobalThis.__fbcPageDescription = localizedPageDescription;",context);
  return{render:context.__fbcRender,pageDescription:context.__fbcPageDescription,manifest};
}

export function cardText(html,tag){
  const found=html.match(new RegExp("<"+tag+">([\\s\\S]*?)</"+tag+">"));assert(found,tag);
  const entities={"&amp;":"&","&lt;":"<","&gt;":">","&#39;":"'","&quot;":'"'};
  return found[1].replace(/&(amp|lt|gt|quot);|&#39;/g,value=>entities[value]);
}
