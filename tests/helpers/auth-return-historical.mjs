// Finite auth-return inverse for historical QA inputs only; never app runtime.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const failure='Unreviewed auth return history',sha=value=>createHash('sha256').update(value).digest('hex');
const require=(value,label)=>assert.ok(value,failure+': '+label),count=(source,part)=>source.split(part).length-1;
const raw=fs.readFileSync(new URL('../fixtures/auth-return-history.json',import.meta.url),'utf8').replace(/\r\n/g,'\n');
require(sha(raw)==='97a8aad3f4b8a0251a80222c7e5af4fe27b1b49e6d1cbfd2dd4f6d19797dfae3','fixture hash');
const fixture=JSON.parse(raw);
require(fixture.base_sha==='fc9aef439d8fe7ecb00a2c68a167dad501f54eb9'&&fixture.records.length===2,'BASE/count');
require(JSON.stringify(fixture.records.map(row=>row.file))===JSON.stringify(['static/portal/portal-auth.js','static/portal/integration.js']),'exact targets');
for(const row of fixture.records){
  require(sha(row.before)===row.before_sha256&&sha(row.after)===row.after_sha256,'record hashes');
}
const signals=['/[\\u0000-\\u001f\\u007f]/.test(route)','normalized === "/api"','normalized === "/internal"','normalized.includes("%")'];
const declarations=/\bfunction\s+safeReturnPath\s*\(/g,owners=/^  (?:async )?function [A-Za-z_][A-Za-z0-9_]*\(/m;

export function authReturnHistoricalSource(source,file){
  require(typeof source==='string','string source');
  const row=fixture.records.find(value=>value.file===file);
  if(!row||!signals.some(signal=>source.includes(signal)))return source;
  const variants=['\n','\r\n'].map(ending=>({
    after:row.after.replace(/\n/g,ending),before:row.before.replace(/\n/g,ending)
  }));
  const matches=variants.filter(value=>source.includes(value.after));
  require(matches.length===1,'one exact complete helper');
  const {after,before}=matches[0];
  require(count(source,after)===1&&[...source.matchAll(declarations)].length===1,'unique helper owner');
  require(count(source,row.previous)===1&&count(source,row.following)===1,'unique adjacent owners');
  const start=source.indexOf(after),previous=source.indexOf(row.previous),following=source.indexOf(row.following);
  const closing=/\r?\n  }\r?\n/g;closing.lastIndex=previous;
  const boundary=closing.exec(source),lower=boundary?boundary.index+boundary[0].length:-1;
  require(previous>=0&&lower>previous&&lower<=start&&start+after.length<=following,'original owner slot');
  require((start===0||source[start-1]==='\n')&&!owners.test(source.slice(lower,start)),'top-level helper placement');
  require(!source.includes(before),'not mixed BASE and current helpers');
  return source.slice(0,start)+before+source.slice(start+after.length);
}
