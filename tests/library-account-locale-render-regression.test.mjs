import assert from 'node:assert/strict';
import test from 'node:test';
import { renderChild } from './helpers/publishing-child-render.mjs';

// These assertions exercise the public renderer, not the presence of helper names.
// They catch missing catalogue entries that silently retain Vietnamese fallbacks.
const accountLeaks = /(?:Đăng nhập Telegram|Đăng nhập Apple|Thành viên Web|Chọn nhanh ảnh đại diện AI có sẵn|Bot công nghệ|Nhà sáng tạo chuyên nghiệp|Cô gái công nghệ AI|Nhà lãnh đạo doanh nghiệp|Công nghệ neon|Nghệ sĩ kỹ thuật số|Tiêu chuẩn|Không khả dụng)/u;
const vietnameseFixedCopy = /\b(?:mới|Chọn nhanh|có sẵn|Thành viên|Đăng nhập)\b/u;

function outerSection(html, marker) {
  const start = html.indexOf(marker);
  assert.ok(start >= 0, 'Expected the actual audio collection board');
  let depth = 0;
  for (const match of html.slice(start).matchAll(/<\/?section\b[^>]*>/g)) {
    depth += match[0].startsWith('</') ? -1 : 1;
    if (!depth) return html.slice(start, start + match.index + match[0].length);
  }
  assert.fail('Board section must be balanced');
}

for (const locale of ['vi', 'en', 'zh']) {
  test(`${locale} Audio Hub board localizes its existing controls without changing collection data`, () => {
    const id = '44444444-4444-4444-8444-444444444444';
    const result = renderChild(locale, `/audio-hub/${id}`, {
      capabilities: { 'media-workspace-view': true },
      mediaCollectionDetail: { collection: { id, title: 'CUSTOMER_AUDIO_TITLE', brief: 'CUSTOMER_AUDIO_BRIEF', state: 'active', revision: 1 }, items: [], versions: [], events: [] },
    });
    assert.match(result.text, /CUSTOMER_AUDIO_TITLE/);
    const board = outerSection(result.html, '<section class="portal-audio-hub-collection-board"');
    assert.match(board, new RegExp(`/media-workspace/${id}`));
    if (locale === 'vi') {
      assert.doesNotMatch(board, /Collection production board|Kiểm tra assembly|Music Directions|Audio Operations|Mở Audio Library editor/);
      const boardText = board.replace(/<[^>]+>/g, ' ');
      assert.doesNotMatch(boardText, /Collection review|session only|readiness|workflow|review|reference|metadata|approval|player|preview|output|delivery|checklist|\baudio\b|\bprivate\b/iu);
    }
    else assert.doesNotMatch(board, /Chưa có tài liệu tham khảo ở nhóm này|Kiểm tra assembly|Mở Audio Library editor/);
  });

  test(`${locale} Audio Library detail keeps customer records while localizing item chrome`, () => {
    const id = '55555555-5555-4555-8555-555555555555';
    const result = renderChild(locale, `/media-workspace/${id}`, {
      capabilities: { 'media-workspace-view': true },
      mediaCollectionDetail: {
        collection: { id, title: 'CUSTOMER_AUDIO_TITLE', brief: 'CUSTOMER_AUDIO_BRIEF', state: 'active', revision: 1 },
        items: [{ id: '66666666-6666-4666-8666-666666666666', role: 'music', title_override: 'CUSTOMER_ITEM_TITLE', delivery: 'guarded', license_note: 'CUSTOMER_LICENSE', asset: { display_name: 'CUSTOMER_AUDIO_FILE', original_filename: 'customer.wav', extension: '.wav', byte_size: 1200 } }],
        versions: [], events: [],
      },
    });
    assert.match(result.text, /CUSTOMER_AUDIO_TITLE|CUSTOMER_ITEM_TITLE|CUSTOMER_AUDIO_FILE/);
    const fixed = result.text.replace(/CUSTOMER_[A-Z_]+/g, '');
    if (locale === 'vi') {
      assert.doesNotMatch(fixed, /Collection production board|Audio Library editor|Music Directions|Audio Operations|Attribution|Tags|Audio reference|Reference|SFX/);
      assert.doesNotMatch(fixed, /Audio Library Briefing|\b(?:audio|private|attachment|waveform|provider preview|text direction|delivery|job|charge|output)\b|Asset Vault/iu);
    }
    else assert.doesNotMatch(fixed, /Vai trò|Tên hiển thị|Ghi chú license|Đánh dấu reference|Tải qua Asset Vault|Gỡ reference|Lưu metadata/);
    assert.match(result.html, /data-portal-action="media-item-update"/);
    assert.match(result.html, /data-media-item-id="66666666-6666-4666-8666-666666666666"/);
  });
}

for (const locale of ['en', 'zh']) {
  for (const route of ['/media-workspace/new', '/image-hub/new']) {
    test(`${locale} ${route} rendered title does not fall back to Vietnamese`, () => {
      const result = renderChild(locale, route, {});
      assert.doesNotMatch(result.title, vietnameseFixedCopy, result.title);
    });
  }

  test(`${locale} account avatar and access labels do not fall back to Vietnamese`, () => {
    const result = renderChild(locale, '/account', {
      profile: {
        displayName: 'CUSTOMER_NAME_UNCHANGED',
        email: 'customer@example.invalid',
        locale,
        accountType: 'web',
      },
      session: { authenticated: true, csrfToken: 'synthetic-local-only' },
      capabilities: {},
    });
    assert.match(result.text, /CUSTOMER_NAME_UNCHANGED/);
    assert.doesNotMatch(result.text, accountLeaks, result.text.slice(0, 700));
  });

  test(`${locale} campaign authoring does not show an untranslated execution note`, () => {
    const result = renderChild(locale, '/campaigns/new', {});
    assert.doesNotMatch(
      result.text,
      /Không có đăng bài, hàng đợi, nhà cung cấp, tác vụ, Xu, PayOS hoặc bàn giao\./u,
    );
  });
}

test('new campaign form does not project an unrelated existing campaign', () => {
  const result = renderChild('vi', '/campaigns/new', {
    campaignPlans: [{
      id: '33333333-3333-4333-8333-333333333333',
      title: 'UNRELATED_EXISTING_CAMPAIGN',
      review_note: 'UNRELATED_EXISTING_NOTE',
      revision: 1,
    }],
    capabilities: { 'campaign-create': true },
  });
  assert.match(result.html, /data-portal-action="campaign-create"/);
  assert.doesNotMatch(result.text, /UNRELATED_EXISTING_(?:CAMPAIGN|NOTE)/);
});

// A directory prefix is not a collection detail: these tools have separate
// authoring forms and must never inherit collection attachment guidance.
for (const locale of ['vi', 'en', 'zh']) {
  for (const [route, action] of [
    ['/media-workspace/music-prompt-composer', 'music-prompt-compose'],
    ['/media-workspace/music-directions', 'music-direction-preset-compose'],
    ['/media-workspace/sfx-cue-sheet', 'sfx-cue-sheet-compose'],
  ]) {
    test(`${locale} ${route} keeps its dedicated tool identity and scope notes`, () => {
      const result = renderChild(locale, route, {});
      assert.doesNotMatch(result.title, /Chi tiết bộ sưu tập âm thanh|Audio collection details|音频合集详情/u);
      assert.doesNotMatch(result.text, /Tham chiếu chỉ trỏ tới Kho tài sản riêng|References point only to the private Asset Vault|参考仅指向私有资产库/u);
      assert.match(result.html, new RegExp(`data-portal-action="${action}"`));
    });
  }
}
