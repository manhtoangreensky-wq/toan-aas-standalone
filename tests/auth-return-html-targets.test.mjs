import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const targets=[
  ['static/portal/portal-auth.js','LOCALES'],
  ['static/portal/integration.js','INTERFACE_LOCALES']
];
const valid=[
  ['/dashboard','/dashboard'],['/dashboard/','/dashboard'],
  ['/voice/tts?lang=en','/voice/tts?lang=en'],['/features?lang=vi','/features?lang=vi'],
  ['/image/create?lang=zh','/image/create?lang=zh'],['/?lang=zh','/?lang=zh'],
  ['/','/'],['/api-tools','/api-tools'],['/apiary','/apiary'],
  ['/internal-tools','/internal-tools'],['/internalized','/internalized']
];
const rejected=[
  '/api','/api/','/api/v1/auth/me','/api?lang=en',
  '/internal','/internal/','/internal/health','/internal?lang=zh',
  '/api%2Fv1%2Fauth%2Fme?lang=en','/%61pi','/foo%2Fbar','/feature%252fapi',
  '/dashboard/../api/v1/auth/me','/x/./dashboard','/a/../../internal',
  '/\tapi','/api\r/v1','/dash\u007fboard',
  'https://example.invalid/','//example.invalid/','/\\example.invalid','/dashboard#private',
  '/login','/register','/password-recovery','/onboarding',
  '/features?lang=en&extra=qa','/features?lang=en&lang=zh','/features?lang=ja',
  '',null,{},123
];
function actual(file,constant){
  const source=fs.readFileSync(file,'utf8').replace(/\r\n/g,'\n');
  const start=source.indexOf('  function safeReturnPath('),end=source.indexOf('\n  }\n',start);
  const localeStart=source.indexOf('  const '+constant+' ='),localeEnd=source.indexOf(';\n',localeStart);
  assert(start>=0&&end>start&&localeStart>=0&&localeEnd>localeStart,'Actual function/locale boundaries');
  const context=vm.createContext({URLSearchParams});
  vm.runInContext(source.slice(localeStart,localeEnd+1)+source.slice(start,end+5)+
    '\nglobalThis.readReturnPath=safeReturnPath;',context);
  return context.readReturnPath;
}
for(const[file,constant]of targets){
  const read=actual(file,constant);
  for(const[input,want]of valid)test(file+' keeps legitimate HTML return '+input,()=>{
    assert.equal(read(input),want);
  });
  for(const[inputIndex,input]of rejected.entries())test(file+' rejects non-HTML/unsafe return #'+inputIndex,()=>{
    assert.equal(read(input),'','Unsafe target must use the existing dashboard fallback, not an API page');
  });
}
