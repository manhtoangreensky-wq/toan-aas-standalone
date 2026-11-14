import test from "node:test";
import assert from "node:assert/strict";
import {chatCardsRenderer} from './helpers/chat-cards-customer-runtime.mjs';

const render=await chatCardsRenderer();
test("Redundant Chat boundary adds neither an empty panel nor availability claims under either permission", () => {
  for(const locale of ['vi','en','zh'])for(const allowed of [false,true]){
    const result=render(locale,'/chat',{chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-run-submit':allowed}});
    assert.equal(result.qa.renderChatWorkspaceBoundary(result.context),'');
  }
});
