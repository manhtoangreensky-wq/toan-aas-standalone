"""Pure system-copy locale contracts; no provider, network or production data."""
import importlib
import itertools
import re
import sys
import pytest

@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "pure-copy.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "owned-pure-copy-test-child-only")
    import socket
    def denied(*args, **kwargs):
        raise AssertionError("Pure copy tests must never use network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    sys.modules.pop("copyfast_video_studio", None)
    return importlib.import_module("copyfast_video_studio")

brand=re.compile(r'TikTok|Facebook|Instagram|Reels|YouTube|Shorts|Telegram|PayOS')
foreign={
'vi':re.compile(r'\b(?:image|media|studio|prompt|plan|review|runtime|asset|bot|web|native|provider|format|owner|account|workflow|engine|editor|continuity|hero|CTA|claim|consent|disclosure|frame|footage|camera|orbit|handheld|ASMR|piano|logo|social|demo|follow|lead|inbox|website|note|ambient|cinematic|electronic|pulse|framing|tracking|transition|visual|hook|shots?|audio|publish|render|preview|output|job|scene)\b',re.I),
'en':re.compile(r'[À-ỹ\u3400-\u9fff]'),
'zh':re.compile(r'[À-ỹ]|\b(?:image|media|studio|prompt|plan|review|runtime|asset|bot|web|provider|format|owner|account|workflow|engine|editor|continuity|hero|CTA|claim|consent|disclosure|frame|footage|camera|orbit|handheld|logo|social|follow|lead|inbox|website|note|ambient|cinematic|electronic|pulse|framing|tracking|transition|visual|audio|publish|render|preview|output|job|scene)\b',re.I)}
identifier='11111111-1111-4111-8111-111111111111';customer='CUSTOMER_LITERAL_{p0}_{p1}_UNCHANGED'
image_ref={'direction_id':identifier,'direction_title':customer,'artboard_id':identifier,'artboard_title':'CUSTOMER_ARTBOARD','language':'vi','aspect_ratio':'9:16','source_image_attached':True}
reference={'asset_id':identifier,'display_name':'CUSTOMER_VIDEO.mp4','extension':'mp4','content_type':'video/mp4','source_video_attached':True}
counts={'image':0,'reference':0};violations=[];checks=0
def system_strings(result,kind):
    values=[result['title'],*result['review_before_use']]
    for key in (('style','motion','music') if kind=='image' else ('direction','platform','goal','tone')):values.append(result[key]['label'])
    for scene in result['scenes']:
        values.extend(scene[key] for key in ('title','visual_direction','camera','transition','audio_direction','editorial_note'))
    return values
def check(video,kind,language,payload,ref,result):
    global checks
    counts[kind]+=1
    assert result['reference']==ref and len(result['scenes'])==3
    assert result['duration_seconds']==payload.duration_seconds
    assert result['scenes'][0]['start_seconds']==0 and result['scenes'][-1]['end_seconds']==payload.duration_seconds
    assert all(s['index']==i+1 and s['end_seconds']>s['start_seconds'] for i,s in enumerate(result['scenes']))
    assert all(result['scenes'][i]['end_seconds']==result['scenes'][i+1]['start_seconds'] for i in range(2))
    for key in (('style','motion','music') if kind=='image' else ('direction','platform','goal','tone')):assert result[key]['id']==getattr(payload,key)
    assert customer in result['title']
    assert all(customer in scene['visual_direction'] for scene in result['scenes'])
    if kind=='reference':assert result['topic']==payload.topic and result['audience']==payload.audience and result['language']==payload.language
    for value in system_strings(result,kind):
        checks+=1;text=brand.sub(' ',value.replace(customer,' ').replace('CUSTOMER_AUDIENCE',' '));found=foreign[language].findall(text)
        if found and len(violations)<40:violations.append({'kind':kind,'language':language,'text':text,'foreign':sorted(set(found))})
    again=video._compose_image_motion_planner(payload,ref) if kind=='image' else video._compose_reference_format_planner(payload,ref)
    assert result==again,'deterministic output'

def test_all_supported_generated_copy_is_localized_and_keeps_customer_structure(video):
    global checks, violations, counts
    checks=0; violations=[]; counts={'image':0,'reference':0}
    for n,(style,motion,music,language) in enumerate(itertools.product(('cinematic','product_reveal','social','editorial'),('slow_push_in','orbit_reveal','handheld_detail','hero_hold'),('none','cinematic_light','modern_electronic','natural_ambience'),('vi','en','zh'))):
        ref={**image_ref,'language':language};payload=video.ImageMotionPlannerRequest(direction_id=identifier,style=style,motion=motion,music=music,duration_seconds=(5,10,15)[n%3]);check(video,'image',language,payload,ref,video._compose_image_motion_planner(payload,ref))
    for n,(direction,platform,goal,tone,language) in enumerate(itertools.product(('product_ad','viral','cinematic','education'),('tiktok','reels','shorts','youtube','facebook','custom'),('follow','sales','lead','website','educate'),('clear','warm','confident','premium','educational'),('vi','en'))):
        payload=video.ReferenceFormatPlannerRequest(asset_id=identifier,direction=direction,platform=platform,goal=goal,tone=tone,topic=customer,audience='CUSTOMER_AUDIENCE',language=language,duration_seconds=(15,30,45,60)[n%4]);check(video,'reference',language,payload,reference,video._compose_reference_format_planner(payload,reference))
    assert counts == {'image':192,'reference':1200}
    assert checks == 36000
    assert violations == [], violations[:5]

def test_unrecognized_image_content_language_only_falls_back_for_system_copy(video):
    reference={**image_ref, 'language':'fr'}
    payload=video.ImageMotionPlannerRequest(direction_id=identifier,style='cinematic',motion='hero_hold',music='none',duration_seconds=10)
    result=video._compose_image_motion_planner(payload, reference)
    assert result['reference']['language'] == 'fr'
    assert result['reference']['direction_title'] == customer
    assert customer in result['title']
    for value in system_strings(result,'image'):
        assert not foreign['vi'].search(brand.sub(' ',value.replace(customer,' ')))

def test_original_request_schema_does_not_gain_new_reference_language_or_accept_unknown_choices(video):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        video.ReferenceFormatPlannerRequest(asset_id=identifier,direction='product_ad',platform='tiktok',goal='educate',tone='clear',topic='Valid new topic',audience='Valid audience',language='zh',duration_seconds=30)
    with pytest.raises(ValidationError):
        video.ImageMotionPlannerRequest(direction_id=identifier,style='made_up',motion='hero_hold',music='none',duration_seconds=10)

@pytest.mark.parametrize('kind,size',[('image',150),('image',155),('image',160),('reference',150)])
def test_translation_prefix_does_not_break_previously_savable_titles(video,kind,size):
    title='X'*size
    if kind=='image':
        ref={**image_ref,'direction_title':title,'language':'vi'}
        payload=video.ImageMotionPlannerPlanSaveRequest(direction_id=identifier,style='cinematic',motion='hero_hold',music='none',duration_seconds=10,destination='video_plan',idempotency_key='owned-prefix-boundary-0001')
        planner=video._compose_image_motion_planner(payload,ref)
        plan,scenes=video._image_motion_planner_to_video_plan(payload,planner)
    else:
        payload=video.ReferenceFormatPlannerPlanSaveRequest(asset_id=identifier,direction='product_ad',platform='tiktok',goal='educate',tone='clear',topic=title,audience='CUSTOMER_AUDIENCE',language='vi',duration_seconds=30,destination='video_plan',idempotency_key='owned-prefix-boundary-0001')
        planner=video._compose_reference_format_planner(payload,reference)
        plan,scenes=video._reference_format_planner_to_video_plan(payload,planner)
    assert plan.title.endswith(title),'The customer title must remain complete, not truncated'
    assert len(plan.title)<=180 and len(scenes)==3
