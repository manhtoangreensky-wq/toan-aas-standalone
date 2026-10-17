import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const auth = fs.readFileSync(path.join(root, "static", "portal", "portal-auth.js"), "utf8");
const integration = fs.readFileSync(path.join(root, "static", "portal", "integration.js"), "utf8");
const app = fs.readFileSync(path.join(root, "app.py"), "utf8");

test("R217-12 keeps the reviewed locale through the guarded login redirect", () => {
  assert.match(app, /f\"\/login\?next=\{quote\(return_target, safe='\/'\)\}\{login_locale\}\"/);
  assert.match(app, /requested_locale in PUBLIC_ACCESS_INTERFACE_LOCALES/);
  for (const source of [auth, integration]) {
    assert.match(source, /const separator = route\.indexOf\("\?"\)/);
    assert.match(source, /entries\.length !== 1/);
    assert.match(source, /entries\[0\]\[0\] !== "lang"/);
    assert.match(source, /encodeURIComponent\(entries\[0\]\[1\]\)/);
  }
});
