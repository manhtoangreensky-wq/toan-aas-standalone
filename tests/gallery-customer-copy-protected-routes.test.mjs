import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {galleryFiles,physicalGallerySources,galleryRendererFromSources} from "./helpers/gallery-customer-copy-render.mjs";
const base="bf95e4017717622d694cbef02fde07799a823a8a";
const before=Object.fromEntries(galleryFiles.map(file=>[file,execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n")]));
const current=await galleryRendererFromSources(physicalGallerySources()),baseline=await galleryRendererFromSources(before);
for(const locale of["vi","en","zh"])for(const route of["/features/image","/image/prompt-composer","/notes","/support"]){
  test(`Gallery change leaves ${locale} ${route} renderer, title and description byte-identical`,()=>{
    const input={profile:{locale,displayName:"CUSTOMER_PROFILE"},capabilities:{}},snapshot=JSON.stringify(input);
    const actual=current(locale,route,input),old=baseline(locale,route,input);
    assert.equal(JSON.stringify(input),snapshot);assert.equal(actual.html,old.html);
    assert.equal(actual.title,old.title);assert.equal(actual.pageDescription,old.pageDescription);
  });
}
