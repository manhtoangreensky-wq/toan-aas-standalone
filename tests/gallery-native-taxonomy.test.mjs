import test from "node:test";
import assert from "node:assert/strict";
import {
  physicalGallerySources, galleryRendererFromSources, galleryContext, galleryEscape
} from "./helpers/gallery-customer-copy-render.mjs";

const render = await galleryRendererFromSources(physicalGallerySources());
const goals = ["sell", "lead", "engagement", "branding", "educate", "organize", "mood"];
const platforms = ["tiktok", "reels", "facebook", "social", "poster", "instagram", "short_video", "notes", "video"];
const expected = {
  vi: ["Bán hàng", "Thu hút khách hàng tiềm năng", "Tương tác", "Xây dựng thương hiệu", "Giáo dục", "Tổ chức nội dung", "Không khí cảm xúc",
    "TikTok", "Reels", "Facebook", "Mạng xã hội", "Áp phích", "Instagram", "Video ngắn", "Ghi chú", "Video"],
  en: ["Sales", "Lead generation", "Engagement", "Brand building", "Education", "Content organization", "Mood",
    "TikTok", "Reels", "Facebook", "Social media", "Poster", "Instagram", "Short video", "Notes", "Video"],
  zh: ["销售", "获取潜在客户", "互动", "品牌建设", "教育", "内容整理", "情绪氛围",
    "TikTok", "Reels", "Facebook", "社交媒体", "海报", "Instagram", "短视频", "笔记", "视频"]
};

function context() {
  const value = galleryContext("detail");
  const catalogue = value.freePromptGalleryCatalog;
  catalogue.total_items = 2;
  catalogue.categories = [
    {id: "category_one", title: "CUSTOMER_CATEGORY", goals, platforms: platforms.slice(0, 8), item_count: 1},
    {id: "category_two", title: "CUSTOMER_CATEGORY_TWO", goals: ["sell"], platforms: ["video"], item_count: 1}
  ];
  catalogue.industries[0].item_count = 2;
  value.freePromptGalleryListing.items[0].goals = goals;
  value.freePromptGalleryDetail.item.goals = goals;
  return value;
}

for (const locale of ["vi", "en", "zh"]) {
  const value = context(), before = JSON.stringify(value);
  const row = render(locale, "/free-prompt-gallery", value);
  for (const [index, id] of [...goals, ...platforms].entries()) {
    test(`Gallery ${locale} renders native taxonomy label for ${id} and retains its option ID`, () => {
      assert(new RegExp(`<option\\b[^>]*value="${id}"[^>]*>${galleryEscape(expected[locale][index])}</option>`).test(row.html),
        `Expected ${locale}/${id} option to retain ID and show ${expected[locale][index]}`);
    });
  }
  test(`Gallery ${locale} uses native goals in tags without translating stored identifiers`, () => {
    for (const label of expected[locale].slice(0, 7)) assert(row.html.includes(`<span>${galleryEscape(label)}</span>`));
    assert(row.html.includes("<span>Facebook</span>"), "Platform tags use the same finite native labels");
    assert.deepEqual(Array.from(row.context.freePromptGalleryDetail.item.goals), goals);
    assert.equal(JSON.stringify(value), before);
  });
  test(`Gallery ${locale} preserves unknown customer taxonomy text and escapes markup`, () => {
    const unknown = 'CUSTOMER_goal_<img src=x onerror="bad()">';
    const custom = galleryContext("detail");
    // A valid enum-shaped unknown ID is still customer data, not translatable copy.
    custom.freePromptGalleryCatalog.categories[0].goals = ["customer_goal"];
    custom.freePromptGalleryListing.items[0].goals = ["customer_goal"];
    custom.freePromptGalleryDetail.item.goals = ["customer_goal"];
    const unknownRow = render(locale, "/free-prompt-gallery", custom);
    assert(unknownRow.html.includes('<span>customer_goal</span>'));
    assert(unknownRow.html.includes('value="customer_goal"'));
    custom.freePromptGalleryDetail.item.prompt = unknown;
    const escaped = render(locale, "/free-prompt-gallery", custom);
    assert(escaped.html.includes(galleryEscape(unknown)));
    assert(!escaped.html.includes("<img src=x"));
  });
}
