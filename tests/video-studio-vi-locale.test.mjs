import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import test from 'node:test';
import { renderChild } from './helpers/publishing-child-render.mjs';

const route = '/video-studio/new';
const id = '11111111-1111-4111-8111-111111111111';
const projectId = '22222222-2222-4222-8222-222222222222';
const sentinel = 'CUSTOMER media Studio Workspace Web URL CSRF metadata Facebook TikTok';
const states = ['ready-empty', 'ready-populated', 'read-only', 'guarded'];
const expectedHashes = {
  en: '86f8949ada36f855fe283fa4ee324bbfe0bf4b0aae72ccebce7353b85c0c5316',
  zh: '728097d5e7e1ebca3cb62cdcdb11d655fe97c713fe0b2cd2e772c5bcef3a703d'
};
const expectedVI = [
  {
    "key": "field.plan.durationHelp",
    "text": "Mục tiêu biên tập để kiểm tra nhịp cảnh, không phải thời lượng tệp đa phương tiện đã tạo."
  },
  {
    "key": "intro.description",
    "text": "Tổ chức kế hoạch video, nhịp cảnh và tự rà soát trong một không gian riêng tư. Các số liệu là thông tin biên tập, không phải tệp đa phương tiện đã được tạo hoặc xác minh."
  },
  {
    "key": "create.description",
    "text": "Bắt đầu bằng mục tiêu, đối tượng, định dạng, tỷ lệ và mô tả. Mỗi lần lưu được máy chủ kiểm tra phiên đăng nhập, mã chống giả mạo, quyền sở hữu, phiên bản và chống gửi lặp."
  },
  {
    "key": "create.note",
    "text": "Không nhập bí mật, chứng từ thanh toán, đường dẫn tệp đa phương tiện hoặc dữ liệu riêng tư không cần thiết."
  },
  {
    "key": "boundary.title",
    "text": "Lập kế hoạch và rà soát, chưa tạo tệp đa phương tiện"
  },
  {
    "key": "boundary.description",
    "text": "Không gian này chỉ lưu mô tả, cảnh và tự rà soát thuộc tài khoản trên ứng dụng này. Trang này không tải lên, dựng, phát, tạo đường dẫn, tệp hoặc bàn giao tệp đa phương tiện."
  },
  {
    "key": "boundary.generation",
    "text": "Tạo tệp đa phương tiện"
  },
  {
    "key": "boundary.render",
    "text": "Dựng tệp đa phương tiện"
  },
  {
    "key": "boundary.delivery",
    "text": "Bàn giao tệp đa phương tiện"
  },
  {
    "key": "empty.plans.description",
    "text": "Tạo kế hoạch đầu tiên để tổ chức mô tả, cảnh và tự rà soát. Không gian này không tạo tệp đa phương tiện hay kết quả thay thế."
  },
  {
    "key": "access.description",
    "text": "Cần phiên đăng nhập hợp lệ để mở các kế hoạch video riêng tư."
  }
];
const rendered = new Map();

function rawFor(state) {
  const populated = state === 'ready-populated';
  return {
    videoStudioEnabled: true,
    videoStudioReadState: state === 'guarded' ? 'guarded' : 'ready',
    capabilities: {
      'video-studio-view': state !== 'guarded',
      'video-plan-create': !['guarded', 'read-only'].includes(state),
      'video-studio-refresh': state !== 'guarded'
    },
    videoStudioSummary: {
      plans: { total: populated ? 1 : 0, draft: 0, review: populated ? 1 : 0,
        approved: 0, archived: 0, limit_per_account: 100 },
      scenes: { active: populated ? 1 : 0, limit_per_plan: 100 }
    },
    videoPlans: populated ? [{
      id, project_id: projectId, title: sentinel, format: 'short_form',
      language: 'en', aspect_ratio: '9:16', target_duration_seconds: 30,
      objective: 'CUSTOMER_OBJECTIVE', audience_excerpt: 'CUSTOMER_AUDIENCE',
      brief_excerpt: sentinel, tags: ['CUSTOMER_TAG'], state: 'review',
      revision: 2, scene_count: 1
    }] : [],
    videoStudioReferences: { projects: [{ id: projectId, title: 'PROJECT ' + sentinel }] }
  };
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const state of states) {
    const raw = rawFor(state);
    const before = JSON.stringify(raw);
    const result = renderChild(locale, route, raw);
    assert.equal(JSON.stringify(raw), before, 'Rendering must not translate or mutate raw user/server fields');
    assert.equal(result.context.videoPlans.length, state === 'ready-populated' ? 1 : 0,
      'The fixture must normalize to the intended populated state');
    assert.equal(result.context.videoStudioReferences.projects.length, 1);
    rendered.set(locale + ':' + state, result);
  }
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const state of states) {
    test(`${locale}:${state} keeps localized copy, state, actions and customer data`, () => {
      const result = rendered.get(locale + ':' + state);
      assert.ok(result.html.length > 100);
      if (state === 'guarded') {
        assert.equal(result.html.includes('data-portal-action="video-plan-create"'), false);
      } else {
        assert.ok(result.html.includes('data-portal-action="video-plan-create"'));
        assert.ok(result.html.includes('data-portal-route="/video-studio/new"'));
        for (const name of ['title', 'format', 'language', 'aspect_ratio',
          'target_duration_seconds', 'objective', 'audience', 'brief', 'tags', 'project_id']) {
          assert.ok(result.html.includes('name="' + name + '"'));
        }
        for (const value of ['short_form', '9:16', '30']) {
          assert.ok(result.html.includes('value="' + value + '"'));
        }
        assert.ok(result.html.includes('PROJECT ' + sentinel));
        const submit = result.html.match(/<button[^>]*type="submit"[^>]*>/)?.[0] || '';
        assert.equal(/\bdisabled\b/.test(submit), state === 'read-only');
        if (state === 'ready-populated') {
          assert.ok(result.text.includes(sentinel));
          assert.ok(result.text.includes('CUSTOMER_TAG'));
          assert.ok(result.html.includes('/video-studio/' + id));
          const plan = result.context.videoPlans[0];
          assert.equal(plan.id, id);
          assert.equal(plan.project_id, projectId);
          assert.equal(plan.language, 'en');
          assert.equal(plan.format, 'short_form');
          assert.equal(plan.aspect_ratio, '9:16');
          assert.equal(plan.target_duration_seconds, 30);
          assert.equal(plan.revision, 2);
        }
      }
      const entries = Object.entries(result.messages[locale])
        .filter(([key]) => key.startsWith('videoStudioUi.'))
        .sort(([left], [right]) => left.localeCompare(right));
      assert.equal(entries.length, 178, 'Do not add or delete Video Studio catalogue keys');
      const keysets = ['vi', 'en', 'zh'].map(language => Object.keys(result.messages[language])
        .filter(key => key.startsWith('videoStudioUi.')).sort());
      assert.deepEqual(keysets[1], keysets[0]);
      assert.deepEqual(keysets[2], keysets[0]);
      if (locale === 'vi') {
        // Only known synthetic data is excluded. Arbitrary customer names are
        // not translated, removed, or forbidden by a blanket page-text rule.
        const fixedCopy = result.text.replaceAll('PROJECT ' + sentinel, '').replaceAll(sentinel, '');
        assert.doesNotMatch(fixedCopy, /\b(?:media|workspace|web|url|csrf|metadata|studio)\b/i,
          'Vietnamese fixed UI must not retain generic English or technical labels');
      } else {
        const hash = crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
        assert.equal(hash, expectedHashes[locale], 'Every existing English/Chinese value must stay unchanged');
      }
    });
  }
}

const removedPresentationKeys = new Set(['intro.description','create.description','boundary.title',
  'boundary.description','boundary.generation','boundary.render','boundary.delivery']);
for (const expected of expectedVI) {
  test('VI retains approved catalogue and presentation: ' + expected.key, () => {
    const state = expected.key === 'access.description' ? 'guarded' : 'ready-empty';
    const result = rendered.get('vi:' + state);
    assert.equal(result.messages.vi['videoStudioUi.' + expected.key], expected.text);
    assert.equal(result.text.includes(expected.text), !removedPresentationKeys.has(expected.key),
      'Useful literals stay visible; explicitly removed boilerplate stays absent');
  });
}
