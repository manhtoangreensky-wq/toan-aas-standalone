import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = fs.readFileSync(path.join(root, "static", "portal", "portal-features.js"), "utf8");

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.className = "";
    this.textContent = "";
    this.innerHTML = "";
    this.children = [];
    this.attributes = {};
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children.filter(Boolean); }
  querySelector() { return null; }
  querySelectorAll() { return []; }
}

const document = { createElement: tag => new Element(tag), getElementById: () => null, querySelector: () => null };
const window = { TOANAASFeatureCatalogCopy: {}, matchMedia: () => ({ matches: false }) };
const sandbox = vm.createContext({ window, document, console, Set, Object, Array, Promise, fetch: async () => ({ ok: false }) });
vm.runInContext(source.replace("window.__TOAN_AAS_FEATURES_READY__ = hydrateFeatures();", "window.__catalogShellTest = { renderSidebar, renderHeader, renderMobile, COPY }"), sandbox);
const { renderSidebar, renderHeader, renderMobile, COPY } = window.__catalogShellTest;

function descendants(node) {
  return [node, ...(node.children || []).flatMap(descendants)];
}

test("Features shell uses the shared SVG icon language and keeps navigation routes", () => {
  const sidebar = new Element("aside");
  renderSidebar(sidebar, COPY.vi);
  const nodes = descendants(sidebar);
  const navLinks = nodes.filter(node => node.className === "portal-nav-link");
  assert.deepEqual(navLinks.map(node => node.attributes.href), ["/dashboard", "/features", "/workspace-menu", "/account", "/legal"]);
  assert.equal(nodes.filter(node => node.className === "portal-sidebar-foot").length, 1);
  assert.equal(nodes.find(node => node.className === "portal-sidebar-foot").children[0].attributes.href, "/legal");
  assert.match(source, /function featureIconMarkup\(icon\)[\s\S]*?<svg class="portal-icon"/u);
  assert.match(source, /iconNode\.innerHTML = featureIconMarkup\(icon\)/u);
  assert.match(source, /close\.innerHTML = featureIconMarkup\("close"\)/u);
  assert.equal(navLinks.some(node => /[⌂◇▦○]/u.test(node.textContent)), false);
});

test("Features header exposes the current location to assistive technology", () => {
  const header = new Element("header");
  renderHeader(header, { email: "qa@example.test", displayName: "QA" }, COPY.vi);
  const nodes = descendants(header);
  const crumbs = nodes.find(node => node.className === "portal-crumbs");
  assert.equal(crumbs.tagName, "NAV");
  assert.equal(crumbs.attributes["aria-label"], COPY.vi.location);
  assert.equal(crumbs.children.at(-1).attributes["aria-current"], "page");
  assert.match(source, /menuIcon\.innerHTML = featureIconMarkup\("menu"\)/u);
});

test("Features mobile route order stays stable while using SVG icons", () => {
  const mobile = new Element("nav");
  renderMobile(mobile, COPY.vi);
  const links = descendants(mobile).filter(node => node.className === "portal-mobile-nav-link");
  assert.deepEqual(links.map(node => node.attributes.href), ["/dashboard", "/features", "/jobs", "/assets", "/account"]);
  assert.match(source, /link\("\/jobs", copy\.work, "work", false, true\)/u);
  assert.match(source, /link\("\/assets", copy\.library, "library", false, true\)/u);
});
