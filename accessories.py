"""Accessory catalogs and source draw-category rules (ArmorIDs, PlayerDrawLayers)."""
from functools import lru_cache
from pathlib import Path
from equipment import ROOT, RULES, in_set

# key -> file prefix, ArmorIDs category, UI name
SLOTS = {'back':('Back','back','背部 / 披风'), 'front':('Front','front','前饰 / 披风'),
         'neck':('Neck','neck','项链'), 'waist':('Waist','waist','腰饰'),
         'shoes':('Shoes','shoe','鞋饰'), 'shield':('Shield','shield','盾牌'),
         'hand_on':('HandsOn','handon','前手饰品'), 'hand_off':('HandsOff','handoff','后手饰品'),
         'face':('Face','face','面部饰品'), 'beard':('Beard','beard','胡须'),
         'balloon':('Balloon','balloon','气球')}
OFFHAND=[(14,20),(14,20),(14,20),(14,18),(14,20),(16,4),(16,16),(18,14),(18,14),(18,14),
         (16,16),(16,16),(16,16),(16,16),(14,14),(14,14),(12,14),(14,16),(16,16),(16,16)]
# ArmorIDs uses the same item key for its back/front components. For example,
# Item.SetDefaults(2287) equips WinterCape Back=6 AND Front=4, not Back=6 alone.
_FRONT_BY_NAME={entry['key']:int(number) for number,entry in RULES['front']['names'].items()}
CAPE_BACK_TO_FRONT={int(number):_FRONT_BY_NAME[entry['key']] for number,entry in RULES['back']['names'].items()
                   if entry['key'] in _FRONT_BY_NAME}
CAPE_FRONT_TO_BACK={front:back for back,front in CAPE_BACK_TO_FRONT.items()}


def path(assets,slot,number): return Path(assets)/'Accessories'/f'Acc_{SLOTS[slot][0]}_{number}.png'


@lru_cache(maxsize=8)
def catalog(assets=ROOT/'Assets'):
    result={}
    for slot,(prefix,category,label) in SLOTS.items():
        entries=[]
        for file in (Path(assets)/'Accessories').glob(f'Acc_{prefix}_*.png'):
            number=int(file.stem.rsplit('_',1)[1])
            info=RULES.get(category,{}).get('names',{}).get(str(number),{'key':file.stem,'label':file.stem})
            entries.append(dict(id=number,name=info['label'],key=info['key'],texture=file.name))
        result[slot]=dict(label=label,items=sorted(entries,key=lambda e:e['id']))
    return result


def validate(raw,assets=ROOT/'Assets'):
    if not isinstance(raw,dict) or set(raw)-SLOTS.keys(): raise ValueError('无效的饰品槽位')
    selected={}
    for slot,number in raw.items():
        if type(number) is not int or number<0: raise ValueError('饰品编号必须为非负整数')
        if number and not any(e['id']==number for e in catalog(assets)[slot]['items']): raise ValueError(f'没有此饰品：{slot} #{number}')
        if number: selected[slot]=number
    return selected


def effective(raw,body,female,auto_capes=True):
    selected=dict(raw)
    # Complete an explicitly chosen cape before applying body-provided capes.
    # An explicitly chosen opposite slot always wins (independent mix-and-match).
    if selected.get('back') in CAPE_BACK_TO_FRONT and not selected.get('front'):
        selected['front']=CAPE_BACK_TO_FRONT[selected['back']]
    elif selected.get('front') in CAPE_FRONT_TO_BACK and not selected.get('back'):
        selected['back']=CAPE_FRONT_TO_BACK[selected['front']]
    if auto_capes:
        mappings=RULES['body']['mappings']
        back=mappings['IncludedCapeBackFemale' if female else 'IncludedCapeBack'].get(str(body),0)
        front=mappings['IncludedCapeFront'].get(str(body),0)
        if body in (85,235,236) and not selected.get('front') and not selected.get('back'):
            back,front={85:(20,7),235:(30,9),236:(31,10)}[body]
        if back and not selected.get('back'): selected['back']=back
        if front and not selected.get('front'): selected['front']=front
    if body and in_set('body','DisableHandOnAndOffAccDraw',body):
        selected.pop('hand_on',None);selected.pop('hand_off',None)
    if body and in_set('body','DisableBeltAccDraw',body) and in_set('waist','IsABelt',selected.get('waist',0)):
        selected.pop('waist',None)
    return selected


def dye_sources(raw,selected):
    """Return the owning dye slot for inferred parts, independent of draw order."""
    sources={slot:slot for slot in selected}
    for slot,opposite,pairs in [('front','back',CAPE_BACK_TO_FRONT),('back','front',CAPE_FRONT_TO_BACK)]:
        if selected.get(slot) and not raw.get(slot):
            sources[slot]=opposite if pairs.get(raw.get(opposite))==selected[slot] else 'body'
    return sources
