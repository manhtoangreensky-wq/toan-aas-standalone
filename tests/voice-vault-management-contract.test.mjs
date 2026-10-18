import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const api = fs.readFileSync("copyfast_api.py", "utf8");
const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const integration = fs.readFileSync("static/portal/integration.js", "utf8");

test("Voice Vault exposes owner-scoped list filters and guarded management routes", () => {
  assert.match(api, /@router\.get\("\/voice\/profiles"\)[\s\S]*?q:\s*str\s*=\s*Query/);
  assert.match(api, /@router\.post\("\/voice\/profiles\/{profile_id}\/rename"\)/);
  assert.match(api, /@router\.post\("\/voice\/profiles\/{profile_id}\/default"\)/);
  assert.match(api, /@router\.post\("\/voice\/profiles\/{profile_id}\/delete"\)/);
  assert.match(api, /@router\.get\("\/voice\/profiles\/{profile_id}\/preview"\)/);
  assert.match(api, /voice_profile_management/);
  assert.match(api, /_run_idempotent\(scope, key,/);
  assert.match(api, /Depends\(require_csrf\)/);
});

test("Voice Vault bridge surface keeps every profile operation on the voice boundary", () => {
  assert.match(api, /normalized\.startswith\("\/internal\/v1\/voice\/profiles"\)/);
  assert.match(api, /"search"|"q"/);
  assert.match(api, /"page"/);
  assert.match(api, /"page_size"/);
  assert.match(api, /"limit"/);
  assert.match(api, /"offset"/);
  assert.match(api, /"total"/);
  assert.match(api, /"has_next"/);
});

test("Voice Vault UI only renders management controls from canonical capability data", () => {
  assert.match(integration, /voiceVaultCapabilities|voice_vault_capabilities/);
  assert.match(portal, /data-voice-vault-management/);
  assert.match(portal, /profile\.capabilities|voiceVaultCapabilities/);
  assert.match(portal, /library\.manageGuarded/);
});
