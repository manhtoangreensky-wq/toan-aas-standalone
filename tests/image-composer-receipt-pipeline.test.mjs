import test from "node:test";
import assert from "node:assert/strict";
import {imageComposerRuntime} from "./helpers/image-composer-native-runtime.mjs";
import {imageComposerReceiptIntegration} from "./helpers/image-composer-receipt-integration.mjs";

const accept = imageComposerReceiptIntegration();
const render = await imageComposerRuntime(), route = "/image/prompt-composer";
const flags = ["browser_result_persisted", "pending_bot_save_created", "telegram_state_changed", "bot_called", "bridge_called",
  "source_image_inspected", "provider_called", "image_created", "output_created", "job_created", "wallet_mutated",
  "payment_started", "asset_saved", "publish_action_created", "delivery_created", "fact_checked", "rights_verified"];
const receipt = {...Object.fromEntries(flags.map(key => [key, false])),
  note: {id: "11111111-1111-4111-8111-111111111111", revision: 2, state: "active", category: "Image Prompt Composer", priority: "normal"},
  destination: "memory_note", selected_variant_index: 0, execution: "web_native_memory_note_server_recomputed",
  draft_recomputed_on_server: true, web_note_persisted: true};
for (const locale of ["vi", "en", "zh"]) for (const index of [0, 1, 2, 3]) {
  test(`${locale}/selection${index}: real API-acceptor to bootstrap to renderer keeps the saved-note receipt`, () => {
    const raw = {...receipt, selected_variant_index: index}, accepted = accept(raw);
    assert(accepted);
    const view = render(locale, route, {imagePromptComposerEnabled: true,
      capabilities: {"image-prompt-compose": true}, imagePromptComposerSaveReceipt: accepted});
    assert(view.context.imagePromptComposerSaveReceipt.note, "Integration must retain the already-validated receipt facts");
    assert(view.qa.renderImagePromptComposerSaveReceipt(view.context.imagePromptComposerSaveReceipt).includes('href="/notes"'));
    assert.equal(view.context.imagePromptComposerSaveReceipt.selected_variant_index, index);
  });
}
test("integration continues to reject every non-false execution boundary", () => {
  for (const key of flags) for (const value of [true, "false", 0, null, undefined]) {
    assert.equal(accept({...receipt, [key]: value}), null, key);
  }
});
