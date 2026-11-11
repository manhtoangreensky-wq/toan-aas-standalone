import assert from 'node:assert/strict';
import test from 'node:test';
import {renderPlainLanguage,sectionWith} from './helpers/account-plain-language-render.mjs';

const locales=['vi','en','zh'];
const technical=/CSRF|OAuth|BOT_USERNAME|canonical|metadata|signed session|元数据|已签名会话|nguồn chuẩn|siêu dữ liệu|cấu hình máy chủ|服务器.*配置/i;
const escapes=/&lt;img|&lt;script/;
const readable=html=>html.replace(/<[^>]+>/g,' ')+' '+[...html.matchAll(/\b(?:title|data-portal-confirm)="([^"]*)"/g)].map(match=>match[1]).join(' ');
const accountRaw=enabled=>({profile:{displayName:'OWNED <img src=x onerror=alert(1)>',email:'owned@example.invalid',locale:'vi',timezone:'Asia/Ho_Chi_Minh',loginMethods:{email:true,google:!enabled}},
  capabilities:{'update-profile':enabled,'link-oauth-google':enabled,'link-oauth-telegram':enabled,'auth-logout':enabled},
  oauthProviders:{google:{enabled},telegram:{enabled}},telegramConnection:{bot_chat_url:enabled?'https://t.me/toanaas_bot':''}});

for(const locale of locales) {
  for(const enabled of [false,true]) test(`${locale}: profile keeps editable fields and honest permission state, without audit boilerplate (${enabled})`,()=>{
    const {html,messages,context}=renderPlainLanguage(locale,'/account',accountRaw(enabled));
    const editor=sectionWith(html,messages['accountCenter.profile.editorTitle']);
    assert.doesNotMatch(readable(editor),technical,'Actual subtitle and disabled hint are customer-readable');
    assert.equal(editor.includes(messages['accountCenter.profile.editorAuditNote']),false,'No repeated implementation/audit note');
    const form=editor.match(/<form\b[\s\S]*?<\/form>/)?.[0];assert.ok(form);
    for(const name of ['display_name','avatar_url','locale','timezone'])assert.ok(form.includes('name="'+name+'"'));
    const submit=form.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0];assert.ok(submit);
    assert.equal(/\bdisabled\b/.test(submit),!enabled);assert.ok(html.includes('data-portal-action="update-profile"'));
    assert.match(html,escapes);assert.equal(context.profile.displayName,'OWNED <img src=x onerror=alert(1)>');
    assert.ok(html.includes('href="/account/security"'));assert.ok(html.includes('href="/account/data-controls"'));
  });
  test(`${locale}: login copy removes protocol jargon but keeps same-account warning and confirmation`,()=>{
    const {html,messages}=renderPlainLanguage(locale,'/account',accountRaw(true));
    const methods=sectionWith(html,messages['accountCenter.profile.methodsTitle']);assert.doesNotMatch(readable(methods),technical);
    assert.match(methods,/data-portal-action="link-oauth-google"/);assert.match(methods,/data-portal-confirm="[^\"]+"/);
    const warning=messages['accountCenter.profile.methodsBody'];
    if(locale==='vi'){assert.match(warning,/cùng một tài khoản Telegram/);assert.match(warning,/không tự gộp.*email/);}
    if(locale==='en'){assert.match(warning,/same Telegram account/);assert.match(warning,/not automatically merged.*email/);}
    if(locale==='zh'){assert.match(warning,/同一个 Telegram 账户/);assert.match(warning,/不会.*邮箱.*自动合并/);}
    assert.ok(methods.includes(warning));assert.doesNotMatch(html,/Google OAuth|GitHub OAuth|Google \(OAuth\)/);
  });
  for(const outcome of ['linked','already-linked','denied'])test(`${locale}: ${outcome} link result stays visible and actionable without protocol labels`,()=>{
    const {html,messages}=renderPlainLanguage(locale,'/account',accountRaw(true),'?oauth='+outcome);
    const key=outcome==='linked'?'oauthNoticeLinked':outcome==='already-linked'?'oauthNoticeAlreadyLinked':'oauthIncompleteBody';
    const body=messages['accountCenter.profile.'+key];assert.ok(html.includes(body));assert.doesNotMatch(body,technical);
    if(outcome==='denied'){
      if(locale==='vi')assert.match(body,/không chia sẻ.*mã/);
      if(locale==='en')assert.match(body,/never share.*codes/);
      if(locale==='zh')assert.match(body,/不要.*分享.*码/);
      assert.ok(html.includes('data-portal-action="link-oauth-google"'));
    }
  });
  for(const enabled of [false,true])test(`${locale}: Bot handoff keeps commands, guards, privacy and deletion boundary (${enabled})`,()=>{
    const {html,messages}=renderPlainLanguage(locale,'/account',accountRaw(enabled));
    const area=sectionWith(html,messages['accountCenter.profile.botCompanionTitle']);assert.doesNotMatch(readable(area),technical);
    for(const command of ['/language','/mode','/profile','/mydata','/data_delete']){
      const button=area.match(new RegExp('<button\\b[^>]*data-copy-text="'+command+'"[^>]*>'))?.[0];assert.ok(button);
      assert.equal(/\bdisabled\b/.test(button),!enabled);
    }
    assert.equal(area.includes('href="https://t.me/toanaas_bot"'),enabled);
    if(enabled)assert.ok(area.includes(messages['accountCenter.profile.botOpenBody']));
    else assert.ok(area.includes(messages['accountCenter.profile.botUnavailableBody']));
    const policy=messages['accountCenter.profile.botDataDeleteBoundary'];assert.ok(area.includes(policy));
    for(const required of ['/data_delete','Telegram','Xu','PayOS'])assert.ok(policy.includes(required));
    assert.ok(area.includes(messages['accountCenter.profile.botDataDeleteBody']));
  });
  test(`${locale}: Dashboard has useful account/work help, no internal assurance box`,()=>{
    const {html,messages}=renderPlainLanguage(locale,'/dashboard',{dashboardReadState:'guarded'});
    for(const key of ['account.body','account.unlinkedBody','work.body','canonical.guardedBody']){
      const value=messages['dashboard.'+key];assert.ok(html.includes(value));assert.doesNotMatch(value,technical);
    }
    assert.doesNotMatch(html,/portal-dashboard-assurance/);
    assert.ok(html.includes('href="/onboarding"'));assert.ok(html.includes('href="/account/security"'));
    assert.match(html,/data-state="guarded"/);
  });
  for(const state of ['loading','failed','ready'])test(`${locale}: Dashboard ${state} remains a real distinct read state`,()=>{
    const {html,messages}=renderPlainLanguage(locale,'/dashboard',{dashboardReadState:state,capabilities:{'dashboard-refresh':true}});
    assert.match(html,new RegExp('data-state="'+state+'"'));
    if(state==='failed'){assert.ok(html.includes(messages['dashboard.canonical.failedBody']));assert.match(html,/data-portal-action="dashboard-refresh"/);}
    if(state==='loading'){assert.match(html,/aria-busy="true"/);assert.ok(html.includes(messages['dashboard.canonical.loadingBody']));}
  });
}
