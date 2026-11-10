import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import test from 'node:test';
import { renderChild, plain } from './helpers/publishing-child-render.mjs';

// Independent, coordinator-reviewed literal translations. Renderer code is
// not used to derive expectations; only fixed result chrome is translated.
const copy = {
  motion: { namespace: "videoMotionResultUi", rows: [
    ["selected","Selected direction","Hướng đã chọn","Selected direction","已选方向"],
    ["custom","Custom direction","Hướng tự chọn","Custom direction","自定义方向"],
    ["videoPrompt","Video prompt","Mô tả tạo video","Video prompt","视频提示词"],
    ["motion","Motion","Chuyển động","Motion","运动"],
    ["audio","Audio direction","Định hướng âm thanh","Audio direction","音频方向"],
    ["customNote","Chủ đề tự nhập được dùng trực tiếp; không có gợi ý Bot hoặc card ẩn nào được chọn thay bạn.","Chủ đề tự nhập được dùng trực tiếp; không có gợi ý hay thẻ ẩn nào được chọn thay bạn.","Your custom topic is used directly; no suggestion or hidden card is selected for you.","直接使用您输入的主题，不会代您选择建议或隐藏卡片。"],
    ["kicker","Web-native deterministic motion guide","Hướng dẫn chuyển động","Motion guide","运动指南"],
    ["fallbackTitle","Creative Motion Guide","Hướng dẫn chuyển động sáng tạo","Creative motion guide","创意运动指南"],
    ["boundary","Đây là text direction để review, không phải image, video, audio, preview, output hay xác nhận provider.","Đây là định hướng bằng văn bản để rà soát, không phải hình ảnh, video, âm thanh, bản xem trước, tệp đầu ra hay xác nhận từ nhà cung cấp.","These are text directions for review, not images, video, audio, a preview, output files or provider confirmation.","这些是供检查的文字方向，并非图像、视频、音频、预览、输出文件或供应商确认。"],
    ["stale","Các lựa chọn ở form đã thay đổi. Guide bên dưới vẫn được giữ để so sánh nhưng không còn khớp form hiện tại; hãy tạo lại khi đã sẵn sàng.","Các lựa chọn trong biểu mẫu đã thay đổi. Hướng dẫn bên dưới được giữ để so sánh nhưng không còn khớp biểu mẫu hiện tại; hãy tạo lại khi đã sẵn sàng.","The form selections have changed. The guide below is kept for comparison but no longer matches the current form; recreate it when ready.","表单选项已更改。下方指南保留用于比较，但已不再匹配当前表单；准备好后请重新创建。"],
    ["idea15","15-second idea","Ý tưởng 15 giây","15-second idea","15秒创意"],
    ["idea30","30-second idea","Ý tưởng 30 giây","30-second idea","30秒创意"],
    ["map","Motion map","Sơ đồ chuyển động","Motion map","运动安排"],
    ["rhythm","Nhịp chuyển động có thể review","Rà soát nhịp chuyển động","Review the motion rhythm","检查运动节奏"],
    ["timelineNote","Đây là direction timeline, không có footage, player, render timeline hoặc output media.","Đây là trình tự định hướng, không có cảnh quay, trình phát, dòng thời gian dựng phim hoặc tệp đa phương tiện đầu ra.","This is a sequence of directions, not footage, a player, an editing timeline or media output.","这是方向顺序，并非素材、播放器、剪辑时间线或媒体输出。"],
    ["imagePrompt","Image prompt direction","Mô tả tạo hình ảnh","Image prompt direction","图像提示词方向"],
    ["motionPrompt","Video motion prompt","Mô tả chuyển động video","Video motion prompt","视频运动提示词"],
    ["camera","Camera motions","Chuyển động máy quay","Camera movements","镜头运动"],
    ["overlay","Text overlay","Chữ trên màn hình","On-screen text","画面文字"],
    ["voiceover","Voiceover","Lời thuyết minh","Voiceover","旁白"],
    ["cta","CTA","Lời kêu gọi hành động","Call to action","行动号召"],
    ["review","Rà soát trước khi dùng ở workflow khác","Rà soát trước khi dùng trong quy trình khác","Review before using in another workflow","用于其他流程前请检查"],
    ["footer","Guide chỉ tồn tại trong state phiên đã xác thực. Trang này không tự lưu, gửi prompt tới engine/provider, xuất file hoặc tạo video.","Hướng dẫn chỉ được giữ trong phiên đăng nhập hiện tại. Trang này không tự lưu, gửi mô tả tới bộ xử lý hoặc nhà cung cấp, xuất tệp hay tạo video.","The guide is kept only in the current signed-in session. This page does not automatically save, send prompts to an engine or provider, export files or create video.","指南仅保存在当前登录会话中。此页面不会自动保存、向引擎或供应商发送提示词、导出文件或创建视频。"],
    ["open","Mở Video Studio","Mở không gian video","Open video workspace","打开视频工作区"]
  ] },
  roadmap: { namespace: "videoRoadmapResultUi", rows: [
    ["emptyKicker","Reviewable planning receipt","Kết quả lập kế hoạch","Planning result","规划结果"],
    ["emptyTitle","Chưa có Long-form Roadmap","Chưa có kế hoạch video dài","No long-form video roadmap yet","暂无长视频规划"],
    ["emptyBody","Điền topic, thời lượng, phong cách và cấu trúc để server trả outline, chapter roadmap, character bible và prompt areas. Browser không tự dựng transcript, preview hoặc video trước khi có phản hồi an toàn.","Điền chủ đề, thời lượng, phong cách và cấu trúc để nhận dàn ý, kế hoạch từng chương, hồ sơ nhân vật và các phần mô tả tạo nội dung. Trình duyệt không tự tạo bản chép lời, bản xem trước hoặc video khi chưa có phản hồi hợp lệ từ máy chủ.","Enter a topic, duration, style and structure to receive an outline, chapter roadmap, character guide and prompt sections. The browser does not create a transcript, preview or video without a valid server response.","填写主题、时长、风格和结构后可获取大纲、章节规划、角色指南和提示词部分。浏览器不会在收到有效服务器响应前自行创建转录、预览或视频。"],
    ["confirm","Lưu Long-form Roadmap hiện tại thành Video Plan Draft? Máy chủ sẽ tự tạo lại roadmap từ lựa chọn đã xác nhận; không tạo pending Telegram/Bot state, không gọi provider, không tạo media/job, không đổi ví Xu, PayOS, asset, publish hoặc delivery.","Lưu kế hoạch video dài hiện tại thành bản nháp kế hoạch video? Máy chủ sẽ tạo lại kế hoạch từ các lựa chọn đã xác nhận; không tạo trạng thái chờ trên Telegram hoặc trợ lý tự động, không gọi nhà cung cấp, không tạo tệp đa phương tiện hay tác vụ, không thay đổi ví Xu, PayOS, tài nguyên, xuất bản hoặc bàn giao.","Save the current long-form roadmap as a video plan draft? The server recomputes it from confirmed selections; no pending Telegram or bot state, provider call, media or job creation, wallet or PayOS change, asset, publication or delivery is created.","将当前长视频规划保存为视频计划草稿？服务器会根据已确认选项重新生成规划；不会创建Telegram或机器人待处理状态、调用供应商、创建媒体或任务、更改Xu钱包或PayOS、创建资源、发布或交付。"],
    ["save","Lưu thành Video Plan","Lưu thành kế hoạch video","Save as video plan","保存为视频计划"],
    ["chapter","Chapter","Chương","Chapter","章节"],
    ["chapterNote","Planning text để review — không có footage, provider, renderer, preview hoặc output media.","Văn bản lập kế hoạch để rà soát — không có cảnh quay, nhà cung cấp, bộ dựng, bản xem trước hoặc tệp đa phương tiện đầu ra.","Planning text for review — no footage, provider, renderer, preview or media output.","供检查的规划文字，不包含素材、供应商调用、渲染、预览或媒体输出。"],
    ["objective","Objective","Mục tiêu","Objective","目标"],
    ["hook","Hook","Mở đầu thu hút","Opening hook","吸引注意的开场"],
    ["script","Script beat","Nhịp kịch bản","Script beat","脚本节奏"],
    ["visual","Visual direction","Định hướng hình ảnh","Visual direction","视觉方向"],
    ["voice","Voice direction","Định hướng giọng đọc","Voice direction","配音方向"],
    ["music","Music / SFX direction","Định hướng nhạc và hiệu ứng âm thanh","Music and sound effects direction","音乐与音效方向"],
    ["transition","Transition","Chuyển cảnh","Transition","转场"],
    ["imagePrompt","Image prompt area","Mô tả tạo hình ảnh","Image prompt section","图像提示词部分"],
    ["videoPrompt","Video prompt area","Mô tả tạo video","Video prompt section","视频提示词部分"],
    ["kicker","Web-native deterministic Long-form Roadmap","Kế hoạch video dài","Long-form video roadmap","长视频规划"],
    ["fallbackTitle","Long-form Video Roadmap","Kế hoạch video dài","Long-form video roadmap","长视频规划"],
    ["minutes","phút","phút","minutes","分钟"],
    ["boundary","Đây là roadmap text để review, không phải video, preview, asset, output hoặc xác nhận provider.","Đây là kế hoạch bằng văn bản để rà soát, không phải video, bản xem trước, tài nguyên, tệp đầu ra hoặc xác nhận từ nhà cung cấp.","This is a text roadmap for review, not a video, preview, asset, output file or provider confirmation.","这是供检查的文字规划，并非视频、预览、资源、输出文件或供应商确认。"],
    ["style","Style:","Phong cách:","Style:","风格："],
    ["structure","Structure:","Cấu trúc:","Structure:","结构："],
    ["chapters","chapters","chương","chapters","章"],
    ["audience","Audience:","Khán giả:","Audience:","受众："],
    ["outline","Overall outline","Dàn ý tổng thể","Overall outline","总体大纲"],
    ["outlineTitle","Mạch nội dung tổng thể","Mạch nội dung tổng thể","Overall narrative","整体叙事脉络"],
    ["outlineEmpty","Chưa có outline an toàn.","Chưa có dàn ý hợp lệ.","No valid outline yet.","暂无有效大纲。"],
    ["continuity","Character / continuity bible","Hồ sơ nhân vật và tính nhất quán","Character and continuity guide","角色与连贯性指南"],
    ["continuityTitle","Giữ mạch xuyên suốt","Giữ mạch xuyên suốt","Maintain continuity","保持连贯性"],
    ["continuityEmpty","Chưa có continuity guidance an toàn.","Chưa có hướng dẫn giữ tính nhất quán hợp lệ.","No valid continuity guidance yet.","暂无有效的连贯性指南。"],
    ["roadmap","Chapter roadmap","Kế hoạch từng chương","Chapter roadmap","章节规划"],
    ["reviewableChapters","chương có thể review","chương để rà soát","chapters for review","章供检查"],
    ["chaptersNote","Mỗi chapter là text direction riêng. Không tạo transcript, voice, music, image, video, render, job hoặc file delivery.","Mỗi chương có định hướng bằng văn bản riêng. Không tạo bản chép lời, giọng đọc, nhạc, hình ảnh, video, bản dựng, tác vụ hoặc tệp bàn giao.","Each chapter has its own text directions. No transcript, voice, music, image, video, render, job or delivery file is created.","每章都有独立的文字方向。不会创建转录、配音、音乐、图像、视频、渲染、任务或交付文件。"],
    ["audioReview","Audio, caption & review","Âm thanh, chú thích và rà soát","Audio, caption and review","音频、配文与检查"],
    ["beforeUse","Chốt nội dung trước khi dùng ở workflow khác","Chốt nội dung trước khi dùng trong quy trình khác","Finalize content before using in another workflow","用于其他流程前请确认内容"],
    ["audio","Audio direction","Định hướng âm thanh","Audio direction","音频方向"],
    ["caption","Caption","Chú thích","Caption","配文"],
    ["cta","CTA","Lời kêu gọi hành động","Call to action","行动号召"],
    ["review","Rà soát trước khi dùng ở nơi khác","Rà soát trước khi dùng ở nơi khác","Review before using elsewhere","用于其他地方前请检查"],
    ["reviewFallback","Luôn kiểm tra claim, quyền sử dụng, consent và brand safety trước khi đưa roadmap sang workflow khác.","Luôn kiểm tra các nhận định, quyền sử dụng, sự đồng ý và an toàn thương hiệu trước khi đưa kế hoạch sang quy trình khác.","Check claims, usage rights, consent and brand safety before taking the roadmap into another workflow.","将规划用于其他流程前，请检查声明、使用权、同意和品牌安全。"],
    ["saveKicker","Bước lưu Web-native","Lưu kế hoạch","Save the plan","保存计划"],
    ["saveTitle","Xác nhận lưu thành Video Plan Draft","Xác nhận lưu thành bản nháp kế hoạch video","Confirm saving as a video plan draft","确认保存为视频计划草稿"],
    ["saveBody","Chỉ gửi lại các lựa chọn brief gốc trong phiên này. Server tự dựng lại outline/chapter roadmap trước khi tạo plan owner-only; browser không gửi chapter/prompt đã render hoặc state Telegram.","Chỉ gửi lại các lựa chọn mô tả gốc trong phiên này. Máy chủ tạo lại dàn ý và kế hoạch từng chương trước khi tạo kế hoạch riêng tư của tài khoản; trình duyệt không gửi nội dung chương, mô tả đã hiển thị hoặc trạng thái Telegram.","Only the original brief selections from this session are resubmitted. The server rebuilds the outline and chapter roadmap before creating a private account-owned plan; the browser does not send rendered chapters, prompts or Telegram state.","仅重新提交本会话中的原始描述选项。服务器会先重建大纲和章节规划，再创建账户私有计划；浏览器不会发送已显示的章节、提示词或Telegram状态。"],
    ["saveNote","Lưu plan không phải render: không có Bot/bridge/provider, source media, image/video/audio, preview, output, job, ví Xu, PayOS, asset, publish, delivery, approval, lock hoặc generation.","Lưu kế hoạch không phải dựng phim: không gọi trợ lý tự động, cầu nối hay nhà cung cấp; không xử lý tệp nguồn, tạo hình ảnh, video, âm thanh, bản xem trước, tệp đầu ra, tác vụ, tài nguyên, xuất bản, bàn giao, phê duyệt, khóa hoặc tạo nội dung; không thay đổi ví Xu hay PayOS.","Saving a plan is not rendering: it does not call a bot, bridge or provider; process source media; create images, video, audio, previews, output, jobs or assets; publish, deliver, approve, lock or generate content; or change the Xu wallet or PayOS.","保存计划并非渲染：不会调用机器人、桥接或供应商，处理源媒体，创建图像、视频、音频、预览、输出、任务或资源，发布、交付、审批、锁定或生成内容，也不会更改Xu钱包或PayOS。"],
    ["open","Mở Video Studio","Mở không gian video","Open video workspace","打开视频工作区"]
  ] }
};
const sentinel = 'CUSTOMER Studio media Facebook TikTok & tên riêng';
const text = name => name + ' ' + sentinel;
const locales = ['vi', 'en', 'zh'];
const catalogBaseline = {
  vi: '541fc676cc74b46ba6e8ac70443ed63dd413126bc167a1d6d6f70ca2fdd69869',
  en: '46bf4a9d8faabb617b770a775add1058a1cfc9a2f85d0b5f8c5a74af175a0d93',
  zh: '28e1ad15992e7f83b46aa985b5b1f6314dba0b7270509b14a0ac4c8f8cb79214'
};
const motionFlags = [
  'input_persisted', 'telegram_state_changed', 'bot_called', 'bridge_called',
  'source_media_inspected', 'media_uploads', 'provider_called', 'image_created',
  'video_created', 'audio_created', 'preview_created', 'output_created',
  'job_created', 'wallet_mutated', 'payment_started', 'asset_saved',
  'publish_action_created', 'delivery_created', 'fact_checked', 'rights_verified'
];
const roadmapFlags = [
  'input_persisted', 'telegram_state_changed', 'bot_called', 'bridge_called',
  'source_media_inspected', 'provider_called', 'image_created', 'video_created',
  'audio_created', 'preview_created', 'output_created', 'job_created',
  'payment_started', 'wallet_mutated', 'asset_saved', 'publish_action_created',
  'fact_checked', 'rights_verified'
];

function motionRaw(state) {
  if (state === 'empty') return { creativeMotionGuideResult: {} };
  const custom = state === 'custom';
  const topic = text('TOPIC');
  const guide = {
    title: text('GUIDE_TITLE'), topic_kind: custom ? 'custom' : 'product',
    topic, language: 'en', style: { id: 'cinematic', label: text('STYLE') },
    suggestion_set: custom ? 0 : 2,
    selected_suggestion: custom ? null : {
      index: 2, title: topic, video_prompt: text('SELECTED_PROMPT'),
      motion: text('SELECTED_MOTION'), audio_direction: text('SELECTED_AUDIO')
    },
    idea_15_seconds: text('IDEA_15'), idea_30_seconds: text('IDEA_30'),
    timeline: [0, 1, 2, 3].map(index => ({
      index: index + 1, start_seconds: index * 7,
      end_seconds: index === 3 ? 30 : (index + 1) * 7,
      direction: text('TIMELINE_' + index)
    })),
    camera_motions: [0, 1, 2, 3, 4, 5].map(i => text('CAMERA_' + i)),
    image_prompt: text('IMAGE_PROMPT'), video_motion_prompt: text('VIDEO_PROMPT'),
    overlay_lines: [0, 1, 2, 3].map(i => text('OVERLAY_' + i)),
    voiceover: text('VOICEOVER'), cta: text('CTA'),
    cautions: [text('CAUTION_1'), text('CAUTION_2')],
    review_before_use: [text('REVIEW_1'), text('REVIEW_2')]
  };
  return {
    capabilities: { 'creative-motion-guide-compose': true, 'creative-motion-guide-suggest': true },
    creativeMotionGuideResult: {
      guide, execution: 'web_native_deterministic_creative_motion_guide_only',
      ...Object.fromEntries(motionFlags.map(key => [key, false]))
    }
  };
}

function roadmapRaw(state) {
  if (state === 'empty') return { longFormRoadmapResult: {} };
  const roadmap = {
    title: text('ROADMAP_TITLE'), topic_category: 'education', topic: text('TOPIC'),
    audience: text('AUDIENCE'), duration_minutes: 3, target_duration_seconds: 180,
    style: 'professional', style_label: text('STYLE'), structure_mode: 'chapters',
    structure: text('STRUCTURE'), platform: 'facebook', aspect_ratio: '16:9',
    language: 'en', chapter_count: 3,
    outline: [0, 1, 2, 3].map(i => text('OUTLINE_' + i)),
    character_bible: [0, 1, 2, 3].map(i => text('CHARACTER_' + i)),
    chapters: [0, 1, 2].map(i => ({
      index: i + 1, start_seconds: i * 60, end_seconds: (i + 1) * 60,
      title: text('CHAPTER_TITLE_' + i), objective: text('OBJECTIVE_' + i),
      hook: text('HOOK_' + i), script_beat: text('SCRIPT_' + i),
      visual_direction: text('VISUAL_' + i), image_prompt: text('IMAGE_' + i),
      video_prompt: text('VIDEO_' + i), voice_direction: text('VOICE_' + i),
      music_sfx_direction: text('MUSIC_' + i), transition: text('TRANSITION_' + i)
    })),
    audio_direction: text('AUDIO'), caption: text('CAPTION'), cta: text('CTA'),
    review_before_use: [text('REVIEW_1'), text('REVIEW_2')]
  };
  const source = {
    topic_category: roadmap.topic_category,
    topic: state === 'mismatched' ? text('OTHER_TOPIC') : roadmap.topic,
    audience: roadmap.audience, duration_minutes: 3, style: roadmap.style,
    custom_style: '', structure_mode: roadmap.structure_mode,
    custom_structure: '', platform: roadmap.platform, language: roadmap.language
  };
  return {
    capabilities: {
      'long-form-roadmap-compose': true,
      'long-form-roadmap-save-plan': state !== 'disabled',
      'video-plan-create': state !== 'disabled'
    },
    longFormRoadmapResult: {
      roadmap, execution: 'web_native_deterministic_long_form_roadmap_only',
      ...Object.fromEntries(roadmapFlags.map(key => [key, false]))
    },
    longFormRoadmapSaveSource: source
  };
}

function sectionAt(html, start) {
  assert.ok(start >= 0, 'The expected result region must exist');
  const tags = /<\/?section\b[^>]*>/g;
  tags.lastIndex = start;
  let depth = 0;
  for (let match; (match = tags.exec(html));) {
    depth += match[0].startsWith('</') ? -1 : 1;
    if (depth === 0) return html.slice(start, tags.lastIndex);
  }
  assert.fail('The result section must be balanced');
}
function resultRegion(kind, html) {
  if (kind === 'motion') {
    const marker = html.indexOf('data-creative-motion-guide-rendered-result');
    return marker < 0 ? '' : sectionAt(html, html.lastIndexOf('<section', marker));
  }
  const layoutEnd = html.indexOf('</aside></div>');
  assert.ok(layoutEnd >= 0, 'Long-form form/layout boundary must exist');
  return sectionAt(html, html.indexOf('<section', layoutEnd + '</aside></div>'.length));
}
function decode(value) {
  return String(value).replaceAll('&amp;', '&').replaceAll('&quot;', '"')
    .replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>');
}
function outputText(html) {
  const attrs = [...html.matchAll(/\b(?:aria-label|title|data-portal-confirm)="([^"]*)"/g)]
    .map(match => decode(match[1])).join(' ');
  return plain(decode(html)) + ' ' + attrs;
}
function allTextValues(value) {
  if (typeof value === 'string') return value.includes(sentinel) ? [value] : [];
  if (Array.isArray(value)) return value.flatMap(allTextValues);
  if (value && typeof value === 'object') return Object.values(value).flatMap(allTextValues);
  return [];
}

const rendered = new Map();
for (const locale of locales) {
  for (const [kind, states, route, fixture] of [
    ['motion', ['selected', 'custom', 'empty'], '/video-studio/motion-guide', motionRaw],
    ['roadmap', ['allowed', 'disabled', 'mismatched', 'empty'], '/video-studio/long-form-planner', roadmapRaw]
  ]) {
    for (const state of states) {
      const raw = fixture(state);
      const before = JSON.stringify(raw);
      const result = renderChild(locale, route, raw);
      assert.equal(JSON.stringify(raw), before, 'Rendering must not mutate any raw record');
      const projected = kind === 'motion'
        ? result.context.creativeMotionGuideResult.guide
        : result.context.longFormRoadmapResult.roadmap;
      assert.equal(Boolean(projected), state !== 'empty',
        kind + ':' + state + ' fixture must survive the real strict normalizer');
      if (projected) {
        const original = kind === 'motion'
          ? raw.creativeMotionGuideResult.guide
          : raw.longFormRoadmapResult.roadmap;
        assert.equal(JSON.stringify(projected), JSON.stringify(original),
          'The complete valid server projection, including customer text, must remain unchanged');
      }
      rendered.set(locale + ':' + kind + ':' + state, {
        ...result, raw, region: resultRegion(kind, result.html)
      });
    }
  }
}
for (const locale of locales) {
  for (const state of ['selected', 'custom']) {
    const result = rendered.get(locale + ':motion:' + state);
    test(locale + ':motion:' + state + ' preserves dynamic server data and scalar timeline', () => {
      const output = outputText(result.region);
      for (const value of allTextValues(result.raw.creativeMotionGuideResult.guide)) {
        assert.ok(output.includes(value), 'Dynamic text must stay unchanged: ' + value);
      }
      assert.ok(output.includes('0–7s'));
      assert.ok(output.includes('21–30s'));
      assert.ok(output.includes('EN'));
      assert.ok(result.region.includes('data-creative-motion-guide-result-stale hidden role="status"'));
      assert.ok(result.region.includes('href="/video-studio"'));
      assert.equal(/data-portal-action=/.test(result.region), false,
        'The motion result must not gain a save, provider or other action');
    });
    test(locale + ':motion:' + state + ' renders the approved locale for fixed chrome', () => {
      const omitted = state === 'selected'
        ? new Set(['custom', 'customNote', 'fallbackTitle'])
        : new Set(['selected', 'videoPrompt', 'motion', 'audio', 'fallbackTitle']);
      const output = outputText(result.region);
      for (const row of copy.motion.rows) {
        if (omitted.has(row[0])) continue;
        assert.ok(output.includes(row[locales.indexOf(locale) + 2]),
          'Missing fixed ' + locale + ' copy: ' + row[0]);
      }
    });
  }
  test(locale + ':motion:empty renders no fabricated result', () => {
    const result = rendered.get(locale + ':motion:empty');
    assert.equal(result.region, '');
    assert.equal(result.html.includes('data-creative-motion-guide-rendered-result'), false);
  });

  for (const state of ['allowed', 'disabled', 'mismatched']) {
    const result = rendered.get(locale + ':roadmap:' + state);
    test(locale + ':roadmap:' + state + ' preserves server text and the save-source/capability gate', () => {
      const output = outputText(result.region);
      for (const value of allTextValues(result.raw.longFormRoadmapResult.roadmap)) {
        assert.ok(output.includes(value), 'Dynamic text must stay unchanged: ' + value);
      }
      assert.ok(output.includes('FACEBOOK'));
      assert.ok(output.includes('16:9'));
      assert.ok(output.includes('0–60s'));
      assert.ok(output.includes('120–180s'));
      const save = result.region.match(/<button\b[^>]*data-portal-action="long-form-roadmap-save-plan"[^>]*>/)?.[0];
      assert.equal(Boolean(save), state !== 'mismatched',
        'Only a matching server-validated source can offer save');
      if (save) {
        assert.ok(save.includes('data-portal-route="/video-studio/long-form-planner"'));
        assert.equal(/\bdisabled\b/.test(save), state === 'disabled',
          'Matching data alone cannot grant the save capability');
      }
      assert.ok(result.region.includes('href="/video-studio"'));
    });
    test(locale + ':roadmap:' + state + ' renders the approved locale for fixed chrome', () => {
      const omitted = new Set([
        'emptyKicker', 'emptyTitle', 'emptyBody', 'fallbackTitle',
        'outlineEmpty', 'continuityEmpty', 'reviewFallback'
      ]);
      if (state === 'mismatched') { omitted.add('confirm'); omitted.add('save'); }
      const output = outputText(result.region);
      for (const row of copy.roadmap.rows) {
        if (omitted.has(row[0])) continue;
        assert.ok(output.includes(row[locales.indexOf(locale) + 2]),
          'Missing fixed ' + locale + ' copy: ' + row[0]);
      }
    });
  }
  test(locale + ':roadmap:empty shows the localized empty state without a save action', () => {
    const result = rendered.get(locale + ':roadmap:empty');
    const output = outputText(result.region);
    for (const key of ['emptyKicker', 'emptyTitle', 'emptyBody']) {
      const row = copy.roadmap.rows.find(item => item[0] === key);
      assert.ok(output.includes(row[locales.indexOf(locale) + 2]), key);
    }
    assert.equal(result.region.includes('data-portal-action='), false);
  });
  test(locale + ':catalog preserves every preexisting translation and namespace entry', () => {
    const result = rendered.get(locale + ':motion:selected');
    const original = Object.entries(result.messages[locale])
      .filter(([key]) => !key.startsWith('videoMotionResultUi.') && !key.startsWith('videoRoadmapResultUi.')
        && !key.startsWith('videoMotionOptionsUi.') && !key.startsWith('videoRoadmapReceiptUi.')
        && !key.startsWith('videoMotionFormUi.') && !key.startsWith('videoRoadmapFormUi.') && !key.startsWith('videoPlanningMetaUi.')
        && !/^videoPlannerHeader[ABC]Ui\./.test(key) && !/^videoInner(?:Fields|Outer|Result)Ui\./.test(key))
      .sort(([a], [b]) => a.localeCompare(b));
    assert.equal(original.length, 9266);
    assert.equal(crypto.createHash('sha256').update(JSON.stringify(original)).digest('hex'), catalogBaseline[locale]);
    assert.equal(original.filter(([key]) => key.startsWith('videoStudioUi.')).length, 178);
  });
  for (const kind of ['motion', 'roadmap']) {
    test(locale + ':' + kind + ' catalog covers all reviewed fixed result strings', () => {
      const result = rendered.get(locale + ':motion:selected');
      const namespace = copy[kind].namespace;
      for (const row of copy[kind].rows) {
        assert.equal(result.messages[locale][namespace + '.' + row[0]], row[locales.indexOf(locale) + 2],
          'The catalog must include even defensive fallback copy: ' + row[0]);
      }
    });
  }
}
