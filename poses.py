"""Built-in source poses and validated, editable animation frame descriptions."""
import math
from copy import deepcopy
from PIL import Image

ACTIONS = {'idle':'站立','walk':'跑动','jump':'跳跃','swing':'挥动','show':'展示 / 举起','shoot':'射击 / 瞄准'}
# Historical item-specific samples remain readable in saved timelines, but are
# not advertised as general player animations or offered in the main action bar.
LEGACY_ACTIONS = {'thrust':'前刺','eat':'食用','drink':'饮用',
           'drink_long':'回忆药水','mow':'割草','guitar':'弹奏','raise_lamp':'后手举灯'}
FRAMES = {'idle':(0,), 'walk':tuple(range(7,20)), 'jump':(5,), 'swing':(1,2,3),
          'show':(2,), 'shoot':(3,), 'thrust':(3,), 'eat':(3,)*4,
          'drink':(0,)*5, 'drink_long':(2,3), 'mow':(4,3,3,3,2,2,2),
          'guitar':(3,)*7, 'raise_lamp':(0,)}
STRETCHES = {'none':'收拢','quarter':'1/4 伸展','three_quarters':'3/4 伸展','full':'完全伸展'}
STRETCH_ROWS = {'full':0,'three_quarters':1,'quarter':2,'none':3}
DEFAULT_POSE = dict(body_frame=0,head_frame=0,leg_frame=0,direction=1,effect_frame=0,
                    front_arm=dict(enabled=True,stretch='full',angle=0),
                    back_arm=dict(enabled=True,stretch='full',angle=0))
for _part in ('head','body','legs','whole'):
    DEFAULT_POSE[_part+'_transform'] = dict(angle=0,x=0,y=0)
MAX_SEQUENCE = 120


def bounded(value, lo, hi, name, integer=False):
    if type(value) not in ((int,) if integer else (int,float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'{name} 必须为 {lo}–{hi} 的'+('整数' if integer else '数值'))
    return value


def shooting_pose(aim_angle=0):
    """Player.ItemCheck_Shoot + PlayerFrame, ordinary useStyle=5, normal gravity.

    World-space degrees: right=0, down=90. The mouse angle is continuous;
    bodyFrame 2/3/4 are alternatives selected by elevation, never a timeline.
    Vanilla's generic branch does not set continuously rotated composite arms.
    """
    bounded(aim_angle,-180,180,'瞄准角度')
    angle=math.radians(aim_angle)
    direction=1 if -90 <= aim_angle <= 90 else -1
    elevation=math.atan2(math.sin(angle),abs(math.cos(angle)))
    frame=2 if elevation < -0.75 else 4 if elevation > 0.6 else 3
    pose=deepcopy(DEFAULT_POSE)
    pose.update(body_frame=frame,head_frame=frame,direction=direction)
    pose['front_arm']['enabled']=False;pose['back_arm']['enabled']=False
    return pose


def validate_pose(raw):
    if not isinstance(raw,dict) or set(raw)-DEFAULT_POSE.keys(): raise ValueError('自定义姿势包含未知字段')
    pose=deepcopy(DEFAULT_POSE)
    for part in ('head','body','legs','whole'):
        key=part+'_transform'
        value=raw.get(key,{})
        if not isinstance(value,dict) or set(value)-{'angle','x','y'}: raise ValueError('无效的部位变换')
        pose[key].update(value)
        for field,limit in [('angle',180),('x',128),('y',128)]:
            bounded(pose[key][field],-limit,limit,key+'.'+field)
    for key in ('body_frame','head_frame','leg_frame'):
        pose[key]=bounded(raw.get(key,pose[key]),0,19,key,True)
    pose['effect_frame']=bounded(raw.get('effect_frame',0),0,7,'饰品动画帧',True)
    pose['direction']=raw.get('direction',1)
    if type(pose['direction']) is not int or pose['direction'] not in (-1,1): raise ValueError('无效的姿势朝向')
    for key in ('front_arm','back_arm'):
        arm=raw.get(key,pose[key])
        if not isinstance(arm,dict) or set(arm)-{'enabled','stretch','angle'}: raise ValueError('无效的手臂参数')
        arm=pose[key]|arm
        if type(arm['enabled']) is not bool or not isinstance(arm['stretch'],str) or arm['stretch'] not in STRETCHES: raise ValueError('无效的手臂伸展长度')
        bounded(arm['angle'],-180,180,'手臂角度')
        pose[key]=arm
    return pose


def builtin_pose(action, index, direction=1):
    """Composite poses from Player.ItemCheck_UseStyle, sampled at animation phases."""
    if action not in ('eat','drink','mow','guitar','raise_lamp'): return None
    frame=FRAMES[action][index]
    pose=deepcopy(DEFAULT_POSE)
    pose.update(body_frame=frame,head_frame=frame,direction=direction)
    pose['front_arm']['enabled']=False;pose['back_arm']['enabled']=False
    def arm(which,stretch,angle): pose[which+'_arm']=dict(enabled=True,stretch=stretch,angle=angle)
    if action=='eat':
        stretch=['full','three_quarters','quarter','none'][index]
        arm('front',stretch,-90);arm('back',stretch,-90)
    elif action=='drink':
        arm('front','full',-36-72*index/4)
    elif action=='raise_lamp': arm('back','full',-135)
    else:
        stretch=['full','three_quarters','quarter','none','quarter','three_quarters','full'][index]
        if action=='mow': arm('front',stretch,-45);arm('back','full',-11.25)
        else:
            oscillation=math.cos(index/6*2*math.pi)*math.degrees(0.2)
            arm('front',stretch,-45+oscillation);arm('back','quarter',-45-oscillation/2)
    return pose


def validate_sequence(raw):
    if not isinstance(raw,list) or not 1 <= len(raw) <= MAX_SEQUENCE: raise ValueError(f'时间轴需要 1–{MAX_SEQUENCE} 帧')
    result=[]
    for entry in raw:
        if not isinstance(entry,dict): raise ValueError('无效的时间轴帧')
        kind=entry.get('kind')
        allowed={'kind','duration','action','frame'} if kind=='fixed' else {'kind','duration','pose'}
        if kind=='fixed' and entry.get('action')=='shoot': allowed.add('aim_angle')
        if set(entry)-allowed: raise ValueError('时间轴帧包含未知字段')
        duration=bounded(entry.get('duration',100),20,2000,'帧时长',True)
        if duration%10: raise ValueError('帧时长必须为 10ms 的倍数')
        if kind=='fixed':
            action=entry.get('action')
            if action not in FRAMES: raise ValueError('未知固定动作')
            frame=bounded(entry.get('frame',0),0,len(FRAMES[action])-1,'动作帧',True)
            result.append(dict(kind=kind,action=action,frame=frame,duration=duration))
            if action=='shoot': result[-1]['aim_angle']=bounded(entry.get('aim_angle',0),-180,180,'瞄准角度')
        elif kind=='custom': result.append(dict(kind=kind,pose=validate_pose(entry.get('pose',{})),duration=duration))
        else: raise ValueError('帧类型必须为 fixed 或 custom')
    return result


def render_sequence(generator, options, sequence):
    images=[]
    for entry in sequence:
        if entry['kind']=='fixed':
            frame_options=options|{'aim_angle':entry['aim_angle']} if entry['action']=='shoot' else options
            image=generator.compose(**frame_options,action=entry['action'],action_frame=entry['frame'])
        else: image=generator.compose(**options,pose=entry['pose'])
        if image.size==(40,56):
            padded=Image.new('RGBA',(64,80));padded.alpha_composite(image,(12,24));image=padded
        images.append(image)
    left=min(im.info.get('origin',(0,0))[0] for im in images)
    top=min(im.info.get('origin',(0,0))[1] for im in images)
    right=max(im.info.get('origin',(0,0))[0]+im.width for im in images)
    bottom=max(im.info.get('origin',(0,0))[1]+im.height for im in images)
    size=(right-left,bottom-top)
    for i,image in enumerate(images):
        x,y=image.info.get('origin',(0,0))
        padded=Image.new('RGBA',size);padded.alpha_composite(image,(x-left,y-top));images[i]=padded
        padded.info['origin']=(left,top)
    return images
