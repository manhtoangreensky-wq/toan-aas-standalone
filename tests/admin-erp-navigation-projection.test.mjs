import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");

function section(startMarker, endMarker) {
  const start = portal.indexOf(startMarker);
  const end = portal.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `missing source section: ${startMarker}`);
  return portal.slice(start, end);
}

const safeRouteSource = section("function safeCatalogRoute", "function catalogEntryRoute");
const navigationSource = section("function adminErpNavigation(context)", "function adminRouteIcon");

function navigationProjection() {
  return new Function(`
    const MAX_ADMIN_ERP_NAVIGATION_GROUPS = 16;
    const ALLOWED_STATES = new Set(["ready", "read_only", "guarded", "processing"]);
    function uiText(_key, fallback) { return fallback; }
    function adminDeliveryRuntimeNavigationText(_route, _field, fallback) { return fallback; }
    function adminDeliveryRuntimeGroupText(_groupId, _field, fallback) { return fallback; }
    function adminRouteIcon(route) { return route; }
    ${safeRouteSource}
    ${navigationSource}
    return adminErpNavigation;
  `)();
}

test("Admin role/module projection keeps only server-issued safe Admin routes", () => {
  const project = navigationProjection();
  const result = project({
    adminErpNavigation: {
      read_state: "ready",
      canonical_admin: true,
      groups: [{
        id: "operations",
        title: "Vận hành",
        modules: [
          { route: "/admin", title: "Tổng quan", state: "available" },
          { route: "/admin/jobs", title: "Tác vụ", state: "read_only" },
          { route: "/admin/jobs", title: "Trùng", state: "ready" },
          { route: "/admin/../users", title: "Đoạn chấm", state: "ready" },
          { route: "/admin/%2e%2e/users", title: "Đoạn mã hóa", state: "ready" },
          { route: "/admin//users", title: "Hai dấu gạch", state: "ready" },
          { route: "/users", title: "Ngoài Admin", state: "ready" },
          { route: "/admin/approvals", title: "Phê duyệt", state: "mystery" }
        ]
      }]
    }
  });

  assert.deepEqual(result.groups[0].modules.map((module) => module.route), [
    "/admin",
    "/admin/jobs",
    "/admin/approvals"
  ]);
  assert.deepEqual([...result.routes], ["/admin", "/admin/jobs", "/admin/approvals"]);
  assert.equal(result.groups[0].modules[0].state, "read_only");
  assert.equal(result.groups[0].modules[2].state, "guarded");
  assert.equal(result.canonicalAdmin, true);
});

test("Admin role/module projection fails closed until the server manifest is ready", () => {
  const project = navigationProjection();
  const result = project({
    adminErpNavigation: {
      read_state: "loading",
      canonical_admin: true,
      support_role: "manager",
      groups: [{ id: "should-not-render", modules: [{ route: "/admin" }] }]
    }
  });

  assert.deepEqual(result.groups, []);
  assert.equal(result.routes.size, 0);
  assert.equal(result.canonicalAdmin, false);
  assert.equal(result.supportRole, "none");
  assert.equal(result.webLocalAdmin, false);
});
