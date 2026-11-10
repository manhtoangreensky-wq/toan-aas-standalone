export const planId = '11111111-1111-4111-8111-111111111111';
export const sceneId = '33333333-3333-4333-8333-333333333333';
export function savedDetailContext(state = 'draft', kind = 'image', customTags = ['CUSTOMER_TAG']) {
  const tags = kind === 'image'
    ? ['image-motion-planner', 'style-cinematic', 'motion-hero_hold', 'music-none', ...customTags]
    : kind === 'reference'
      ? ['reference-format-planner', 'direction-product_ad', 'platform-tiktok', 'goal-educate', 'tone-clear', ...customTags]
      : [...customTags];
  const plan = {id: planId, project_id: null, title: 'CUSTOMER_TITLE', format: 'short_form', language: 'vi',
    aspect_ratio: '9:16', target_duration_seconds: 30, objective: 'CUSTOMER_OBJECTIVE',
    audience: 'CUSTOMER_AUDIENCE', audience_excerpt: 'CUSTOMER_AUDIENCE', brief: 'CUSTOMER_BRIEF',
    brief_excerpt: 'CUSTOMER_BRIEF', tags, state: ['draft','review','approved','archived'].includes(state) ? state : 'draft',
    revision: 2, scene_count: 1, created_at: '2026-11-11T00:00:00Z', updated_at: '2026-11-11T00:00:00Z'};
  const scene = {id: sceneId, plan_id: planId, ordinal: 1, title: 'CUSTOMER_SCENE', scene_type: 'hook',
    duration_seconds: 30, visual_direction: 'CUSTOMER_VISUAL', narration: 'CUSTOMER_NARRATION',
    on_screen_text: 'CUSTOMER_SCREEN', shot_notes: 'CUSTOMER_NOTE', transition: 'CUSTOMER_TRANSITION',
    tags: kind === 'image' ? ['image-motion-planner','scene-1','motion-hero_hold',...customTags] : [...customTags],
    state: 'active', revision: 2, created_at: '2026-11-11T00:00:00Z', updated_at: '2026-11-11T00:00:00Z',
    versions: [{revision:1,title:'CUSTOMER_OLD_SCENE',created_at:'2026-11-10T00:00:00Z'}]};
  const capabilities = Object.fromEntries(['video-studio-view','video-plan-create','video-plan-update','video-plan-lifecycle',
    'video-plan-restore','video-plan-restore-version','video-scene-create','video-scene-update','video-scene-archive',
    'video-scene-restore','video-scene-restore-version','video-scene-reorder','video-studio-refresh'].map(name => [name,true]));
  if (state === 'guarded') capabilities['video-studio-view'] = false;
  if (state === 'readonly') for (const key of Object.keys(capabilities)) if (!['video-studio-view','video-studio-refresh'].includes(key)) capabilities[key] = false;
  return {videoStudioEnabled:true, videoStudioReadState:['loading','failed','guarded'].includes(state) ? state : 'ready',
    capabilities, videoStudioSummary:{plans:{total:1,review:0,approved:0}}, videoPlans:[plan], videoStudioReferences:{projects:[]},
    videoPlanDetail: ['missing','loading','failed'].includes(state) ? {} : {plan,scenes:[scene],
      versions:[{revision:1,title:'CUSTOMER_OLD_TITLE',format:'short_form',state:'draft',brief_excerpt:'CUSTOMER_OLD_BRIEF',created_at:'2026-11-10T00:00:00Z'}],
      events:[{action:'plan_created',entity_type:'plan',scene_id:null,revision:1,created_at:'2026-11-10T00:00:00Z'}]}};
}
