import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL, fileURLToPath} from 'node:url';

// Catches leaving the static placeholder visible or deleting any real membership
// field, state, approved offer, action, or input while removing that placeholder.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE = '8371c43d147b0074c71c00dc4d3f7f9927894d5c';
const HELPER = path.join(ROOT, 'tests/helpers/publishing-child-render.mjs');
const {renderChild: renderCurrent} = await import(pathToFileURL(HELPER).href);
const basePortal = execFileSync('git', ['show', `${BASE}:static/portal/portal.js`], {
  cwd: ROOT,
  encoding: 'utf8',
  maxBuffer: 30 * 1024 * 1024
});

// Evaluate the real helper unchanged except its root/source loading. The BASE
// renderer still executes the full real portal and the same actual i18n file.
// No renderer, normalizer, projection, formatter or locale helper is replaced.
const realHelperSource = fs.readFileSync(HELPER, 'utf8');
const rootLoader = "const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');";
const portalLoader = "const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');";
assert.equal(realHelperSource.split(rootLoader).length - 1, 1, 'real helper root loader must match once');
assert.equal(realHelperSource.split(portalLoader).length - 1, 1, 'real helper portal loader must match once');
const baselineHelperSource = realHelperSource
  .replace(rootLoader, `const root=${JSON.stringify(ROOT)};`)
  .replace(portalLoader, `const portal=${JSON.stringify(basePortal)};`);
const {renderChild: renderBase} = await import(
  `data:text/javascript;base64,${Buffer.from(baselineHelperSource).toString('base64')}`
);

const emptyCatalogs = {
  packageCatalog: {available: false},
  pricingCatalog: {available: false}
};
const fixtures = {
  'missing-wallet': {
    ...emptyCatalogs,
    walletReadState: 'guarded',
    wallet: null
  },
  'zero-standard': {
    ...emptyCatalogs,
    walletReadState: 'ready',
    wallet: {
      balance_xu: 0,
      total_spent_xu: 0,
      is_vip: false,
      plan: {plan_name: 'SYNTHETIC_ZERO_PLAN', current_plan: 'zero_plan', plan_status: 'ACTIVE_ZERO'}
    }
  },
  VIP: {
    ...emptyCatalogs,
    walletReadState: 'ready',
    wallet: {
      balance_xu: 2500,
      total_spent_xu: 275,
      is_vip: true,
      plan: {plan_name: 'SYNTHETIC_VIP_PLAN', current_plan: 'vip_plan', plan_status: 'ACTIVE_VIP'}
    }
  },
  'populated-approved-catalog': {
    walletReadState: 'ready',
    wallet: {
      balance_xu: 1350,
      total_spent_xu: 125,
      is_vip: false,
      plan: {plan_name: 'SYNTHETIC_CATALOG_PLAN', current_plan: 'catalog_plan', plan_status: 'ACTIVE_CATALOG'}
    },
    packageCatalog: {
      available: true,
      monthly: [{code: 'synthetic_member_month', label: 'SYNTHETIC_MONTHLY_OFFER', note: 'SYNTHETIC_MONTHLY_BENEFIT', manual: false}],
      combos: [{code: 'synthetic_member_bundle', label: 'SYNTHETIC_BUNDLE_OFFER', note: 'SYNTHETIC_BUNDLE_BENEFIT', manual: true}]
    },
    pricingCatalog: {
      available: true,
      image_tiers: [],
      video_tiers: [],
      video_combos: [],
      public_sale_catalog: {
        available: true,
        approval_status: 'owner_approved',
        catalog_version: 'synthetic_membership_v1',
        items: [
          {code: 'synthetic_member_month', family: 'service', label: 'SYNTHETIC_MONTHLY_OFFER', sale_price_xu: 425},
          {code: 'synthetic_member_bundle', family: 'service', label: 'SYNTHETIC_BUNDLE_OFFER', sale_price_xu: 875}
        ]
      }
    }
  }
};

function removeOnlyStaticTierSection(html, required) {
  const openings = [...html.matchAll(/<section\b[^>]*>/g)].filter(match =>
    /class="[^"]*\bportal-pricing-membership\b[^"]*"/.test(match[0])
  );
  assert.ok(openings.length <= 1, 'at most one old static tier section may exist');
  if (!openings.length) {
    assert.equal(required, false, 'BASE must actually render the unwanted static section');
    return {html, count: 0};
  }
  const start = openings[0].index;
  const tags = /<\/?section\b[^>]*>/g;
  tags.lastIndex = start;
  let depth = 0;
  let end = -1;
  for (let match; (match = tags.exec(html));) {
    depth += match[0].startsWith('</') ? -1 : 1;
    if (depth === 0) {
      end = tags.lastIndex;
      break;
    }
  }
  assert.ok(end > start, 'static section must have a real balanced closing tag');
  const section = html.slice(start, end);
  assert.ok(section.includes('Danh mục cấp bậc hội viên thương mại:'), 'remove only the hand-identified static commercial-tier placeholder');
  assert.ok(section.includes('<strong>Không khả dụng</strong>'), 'BASE placeholder really says unavailable');
  assert.ok(section.includes('phiên tài khoản signed session'), 'BASE placeholder really contains the identified implementation filler');
  assert.doesNotMatch(section, /\b(?:href|data-portal-action)=/, 'the removed placeholder must not contain a real customer action');
  // The removed template owns these two whitespace runs as well as its section.
  const prefix = '\n      ', suffix = '\n    ';
  assert.equal(html.slice(start - prefix.length, start), prefix);
  assert.equal(html.slice(end, end + suffix.length), suffix);
  return {html: html.slice(0, start - prefix.length) + html.slice(end + suffix.length), count: 1};
}

function controls(html) {
  return [...html.matchAll(/<(?:a|button|form|input|select|option)\b[^>]*>/g)].map(match => match[0]);
}

function assertRealFixture(result, locale, state, raw) {
  assert.ok(result.html.includes('portal-membership-page'), 'the actual /membership page must render');
  assert.equal(result.context.profile.locale, locale, 'real locale normalization must select the requested locale');
  for (const href of ['/packages', '/pricing', '/wallet/topup']) {
    assert.ok(result.html.includes(`href="${href}"`), `retain real ${href} customer action`);
  }
  const messages = result.messages[locale];
  if (state === 'missing-wallet') {
    assert.equal(result.context.wallet, null, 'missing-wallet fixture must not fabricate wallet data');
    assert.ok(result.html.includes(messages['billingCatalog.membership.empty.title']), 'real missing-benefit state must remain visible');
  } else {
    assert.ok(result.html.includes(raw.wallet.plan.plan_name), 'real current plan name must be visible');
    assert.ok(result.html.includes(raw.wallet.plan.plan_status), 'real current plan status must be visible');
    assert.ok(result.html.includes(`${raw.wallet.balance_xu} Xu`), 'valid zero or positive balance must be visible');
    assert.equal(result.context.wallet.is_vip, state === 'VIP', 'VIP and standard fixtures must take distinct real data states');
  }
  if (state === 'populated-approved-catalog') {
    for (const value of ['SYNTHETIC_MONTHLY_OFFER', 'SYNTHETIC_MONTHLY_BENEFIT', 'SYNTHETIC_BUNDLE_OFFER', 'SYNTHETIC_BUNDLE_BENEFIT', '425 Xu', '875 Xu']) {
      assert.ok(result.html.includes(value), `approved catalog must actually render ${value}`);
    }
    assert.equal((result.html.match(/portal-billing-catalog-card/g) || []).length, 2, 'both real approved offer cards must render');
  } else {
    assert.ok(result.html.includes(messages['billingCatalog.membership.catalog.emptyTitle']), 'real missing-catalog state must remain visible');
  }
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const [state, fixture] of Object.entries(fixtures)) {
    test(`${locale}/${state}: hides only static tier clutter while preserving real membership output and inputs`, () => {
      const raw = {
        ...structuredClone(fixture),
        profile: {locale, displayName: 'SYNTHETIC_MEMBER', accountType: 'telegram'},
        capabilities: {'wallet-view': true, 'package-catalog-view': true}
      };
      const currentInput = structuredClone(raw);
      const baseInput = structuredClone(raw);
      const baseline = renderBase(locale, '/membership', baseInput);
      const current = process.env.MEMBERSHIP_BASELINE === '1'
        ? renderBase(locale, '/membership', currentInput)
        : renderCurrent(locale, '/membership', currentInput);
      assert.deepEqual(baseInput, raw, 'BASE must not mutate raw customer inputs');
      assert.deepEqual(currentInput, raw, 'current renderer must not mutate raw customer inputs');
      assertRealFixture(baseline, locale, state, raw);
      assertRealFixture(current, locale, state, raw);

      const expected = removeOnlyStaticTierSection(baseline.html, true);
      const actualRemainder = removeOnlyStaticTierSection(current.html, false);
      assert.equal(actualRemainder.html, expected.html, 'every remaining HTML byte must equal real BASE output after removing only the old static section');
      assert.deepEqual(controls(current.html), controls(expected.html), 'all real control and link tags must remain identical');
      assert.equal(JSON.stringify(current.context), JSON.stringify(baseline.context), 'normalized actual customer values and read/status data must stay identical');
      assert.equal(actualRemainder.count, 0, 'unwanted static commercial-tier unavailable section is still rendered');
      assert.equal(current.html, expected.html, 'actual output must be exactly BASE minus the single static section, without any replacement blank card');
      assert.equal(current.html.includes('Danh mục cấp bậc hội viên thương mại:'), false, 'unavailable placeholder text must be absent');
    });
  }
}
