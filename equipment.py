"""Terraria 1.4.4 equipment layers; see docs/equipment.md for source references."""
from functools import lru_cache
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
RULES = json.loads((ROOT / 'equipment_rules.json').read_text(encoding='utf-8'))
SLOTS = {'head':('Head','Armor_Head_'), 'body':('Body','Armor_'), 'legs':('Legs','Armor_Legs_')}
# Player.SetMatch: body -> visible robe/skirt leg texture (male, female).
ROBES = {15:88,36:89,41:97,42:90,58:91,59:92,60:93,61:94,62:95,63:96,77:121,
         165:(118,99),166:(119,100),167:(101,102),180:115,181:116,183:(136,123),
         191:131,93:165,90:166,88:168,213:187,215:189,219:196,221:199,223:204,
         231:214,232:215,233:216,241:229}
# DrawPlayer_16_ArmorLongCoat: drawn over the selected pants, before the torso.
COATS = {200:149,202:151,201:150,209:160,207:161,198:162,182:163,168:164,73:170,
         52:(171,172),187:173,205:174,53:(175,176),210:(178,177),211:(182,181),
         218:195,222:(201,200),225:206,236:221,237:223,89:186,81:169}
LEG_MATCH = {83:(117,83),84:(120,84),132:(135,132),57:(137,57),180:(180,179),
             184:(184,183),146:(146,147),154:(155,154),158:(157,158),191:(191,192),
             193:(193,194),197:(197,198),203:(203,202),208:(208,207),219:(219,220),232:(232,233)}


def in_set(slot, name, value):
    rule = RULES[slot]['sets'][name]
    return rule['default'] != (value in rule['exceptions'])


def gender(value, female):
    return value[int(female)] if isinstance(value, tuple) else value


def matched(head, body, legs, female):
    if head == 201 and female:
        head = 202
    if body in ROBES:
        legs = gender(ROBES[body], female)
    elif body == 81 and not legs:
        legs = 169
    legs = gender(LEG_MATCH.get(legs, legs), female)
    return head, body, legs


def armor_path(assets, slot, number):
    folder, prefix = SLOTS[slot]
    return Path(assets) / 'Armor' / folder / f'{prefix}{number}.png'


@lru_cache(maxsize=8)
def equipment_catalog(assets=ROOT / 'Assets'):
    result = {}
    backs = set(RULES['head']['back_ids'].values())
    for slot, (folder, prefix) in SLOTS.items():
        entries = []
        for path in (Path(assets) / 'Armor' / folder).glob(prefix+'*.png'):
            number = int(path.stem.removeprefix(prefix))
            if number == 0 or slot == 'head' and (number in backs or number == 23):
                continue
            info = RULES[slot]['names'].get(str(number), {'key':path.stem,'label':path.stem})
            if slot == 'legs' and info['key']==path.stem:
                for body, value in (ROBES | COATS).items():
                    if number in (value if isinstance(value,tuple) else (value,)):
                        name = RULES['body']['names'].get(str(body),{}).get('label',f'上身 #{body}')
                        info = {'key':path.stem,'label':name+' · 衣摆'}
                        break
            reason = '缺少 Extra_73 神灵诅咒贴图' if slot=='legs' and number==140 and not (Path(assets)/'Armor/Legs/Extra_73.png').is_file() else ''
            entries.append(dict(id=number,name=info['label'],key=info['key'],texture=path.name,
                                available=not reason,note=reason))
        result[slot] = sorted(entries,key=lambda entry:entry['id'])
    return result


def validate_equipment(slot, value, assets=ROOT / 'Assets'):
    if type(value) is not int or value < 0:
        raise ValueError('装备编号必须为非负整数')
    if not value:
        return
    entry = next((e for e in equipment_catalog(assets)[slot] if e['id']==value),None)
    if entry is None:
        raise ValueError(f'没有此装备素材：{slot} #{value}')
    if not entry['available']:
        raise ValueError(entry['note'])


def equipped_textures(config, assets=ROOT / 'Assets'):
    head,body,legs = matched(config['armor_head'],config['armor_body'],config['armor_legs'],config['skin_variant'] in (4,5,6,7,9))
    result = {slot:([armor_path(assets,slot,n).name] if n else []) for slot,n in [('head',head),('body',body),('legs',legs)]}
    if str(head) in RULES['head']['back_ids']:
        result['head'].append(armor_path(assets,'head',RULES['head']['back_ids'][str(head)]).name)
    if body in COATS:
        result['body'].append(armor_path(assets,'legs',gender(COATS[body],config['skin_variant'] in (4,5,6,7,9))).name)
    if legs==140: result['legs']=['Extra_73.png']
    return result


def shoulder_offset(body, frame):
    if body in (55,71,183):
        if frame in (7,8,9,10): return -4
        if frame in (6,11,12,13,18,19) or frame==14 and body!=183: return -2
        if body==183 and frame in (15,16): return 2
    if body==204:
        if frame in (7,8,9): return -2
        if frame in (15,16,17): return 2
    if body in (201,101):
        if frame in (7,8,9,10): return -2
        if frame in ((15,16) if body==201 else (14,15,16,17)): return 2
    if body==207 and frame in (6,7,8,9,10,11,12,13,14,18,19): return -2
    return 0


def compose_equipped(g, c):
    """Composite unlit base armor; retain a 12px side/24px top transparent margin."""
    for slot in SLOTS:
        validate_equipment(slot,c['armor_'+slot],g.assets_path)
    female = c['skin_variant'] in (4,5,6,7,9)
    head, body, legs = matched(c['armor_head'],c['armor_body'],c['armor_legs'],female)
    from accessories import validate, effective, dye_sources, path as accessory_path, OFFHAND, SLOTS as ACCESSORY_SLOTS
    import dyes
    from poses import STRETCH_ROWS
    selected=effective(validate(c.get('accessories') or {},g.assets_path),body,female,c.get('auto_capes',True))
    accessory_dye_sources=dye_sources(c.get('accessories') or {},selected)
    armor_dyes=dyes.validate(c.get('armor_dyes') or {},SLOTS)
    accessory_dyes=dyes.validate(c.get('accessory_dyes') or {},ACCESSORY_SLOTS)
    # Automatically matched robes and long coats use the originating body slot.
    leg_dye_slot='body' if body in ROBES or body==81 and not c['armor_legs'] else 'legs'

    def dyed(sprite, color, tint=None):
        if tint is not None: sprite=g.recolor_image(sprite,tint)
        if color!='#ffffff': sprite=g.recolor_image(sprite,dyes.rgb(color))
        return sprite

    def accessory_color(slot):
        if slot in accessory_dyes: return accessory_dyes[slot]
        source=accessory_dye_sources.get(slot,slot)
        return armor_dyes.get('body','#ffffff') if source=='body' else accessory_dyes.get(source,'#ffffff')
    pose=c.get('pose')
    frame = g._action_body_frame(c['action'],c['action_frame'],c['use_style'])
    head_frame = frame if c['head_frame'] is None else c['head_frame']
    eye_frame = head_frame if c['eye_frame'] is None else c['eye_frame']
    leg_frame = frame if c['action'] in ('walk','jump') else 0
    (bx,by),(fx,fy) = g._composite_arm_cells(frame)
    if pose:
        frame=pose['body_frame'];head_frame=pose['head_frame'];eye_frame=head_frame;leg_frame=pose['leg_frame']
        (bx,by),(fx,fy)=g._composite_arm_cells(frame)
        if pose['front_arm']['enabled']: fx,fy=7,STRETCH_ROWS[pose['front_arm']['stretch']]
        if pose['back_arm']['enabled']: bx,by=8,STRETCH_ROWS[pose['back_arm']['stretch']]
    direction=pose['direction'] if pose else c['direction']
    effect_frame=pose['effect_frame'] if pose else c['action_frame']
    tx,ty = int(frame==5),2 if female else 0
    if c['body_cell'] is not None: tx,ty=c['body_cell']%9,c['body_cell']//9
    bob = -2 if frame in (7,8,9,14,15,16) else 0
    layers = []

    def paste(sprite, x=0, y=0, tint=None, arm=None, part='body'):
        if tint is not None: sprite=g.recolor_image(sprite,tint)
        layers.append((sprite,x+12,y+24,part,arm))

    def arm_at(x,y):
        return 'front' if (x,y)==(fx,fy) else 'back' if (x,y)==(bx,by) else None

    def player(piece, color, x=0, y=0, variant=None, composite=True):
        variant = c['skin_variant'] if variant is None else variant
        src=g._open(g.player_path/g.texture_name(variant,piece))
        if src.getbbox() is None: return
        paste(src.crop((x*40,y*56,x*40+40,y*56+56)),y=bob if composite else 0,tint=c[color],arm=arm_at(x,y) if composite else None,
              part='head' if piece in (0,1,2) else 'legs' if piece in (10,11,12,14) else 'body')

    def armor(slot, number, x=0, y=0, dx=0, dy=0, width=40, height=56, sy=None, tint=None, dye_slot=None):
        if not number: return
        src=g._open(armor_path(g.assets_path,slot,number))
        sy=y*56 if sy is None else sy
        color=armor_dyes.get(dye_slot or (leg_dye_slot if slot=='legs' else slot),'#ffffff')
        sprite=dyed(src.crop((x*40,sy,x*40+width,sy+height)),color,tint)
        paste(sprite,dx,dy,arm=arm_at(x,y) if slot=='body' else None,part='body' if dye_slot=='body' else slot)

    def accessory(slot, number=None, x=0, row=None, dx=0, dy=0, arm=None, tint=None, width=40):
        number=selected.get(slot,0) if number is None else number
        if not number: return
        src=g._open(accessory_path(g.assets_path,slot,number))
        row=frame if row is None else row
        if slot=='shield': width=src.width
        sprite=dyed(src.crop((x*40,row*56,x*40+width,row*56+56)),accessory_color(slot),tint)
        paste(sprite,dx,dy,arm=arm,part='head' if slot in ('face','beard') else 'legs' if slot=='shoes' else 'body')

    def balloon(front):
        number=selected.get('balloon',0)
        if not number or in_set('balloon','DrawInFrontOfBackArmLayer',number)!=front: return
        if in_set('balloon','UsesTorsoFraming',number): accessory('balloon'); return
        src=g._open(accessory_path(g.assets_path,'balloon',number))
        x,y=OFFHAND[frame]
        paste(dyed(src.crop((0,(effect_frame%4)*56,src.width,(effect_frame%4)*56+56)),accessory_color('balloon')),x-20,y-24)

    def front_accessory(front_part):
        # DrawPlayer_32_FrontAcc_FrontPart/BackPart split the BODY rectangle,
        # not the whole texture width. Facing right: x=0..19 goes over the arm;
        # x=20..39 goes behind the arm/shield but over the torso. Flip once later.
        number=selected.get('front',0)
        if not number:return
        src=g._open(accessory_path(g.assets_path,'front',number))
        x=0 if front_part else 20
        sprite=dyed(src.crop((x,frame*56,x+20,frame*56+56)),accessory_color('front'))
        paste(sprite,x,0)

    full = in_set('head','DrawFullHair',head)
    hat = in_set('head','DrawHatHair',head)
    bare = not head or head==259
    show_hair = full or hat or bare
    face=selected.get('face',0)
    face_head=face and in_set('face','DrawInFaceHeadLayer',face)
    if face and (in_set('face','PreventHairDraw',face) or in_set('face','DrawInFaceHeadLayer',face) and head): show_hair=False
    hide_helmet=face and in_set('face','OverrideHelmet',face)
    alt = hat if head else c['alt_hair']
    hair_src = g._open(g.hair_path/f"Player_Hair{'Alt' if alt else ''}_{c['hair']}.png")
    hair = hair_src.crop((0,max(head_frame-6,0)*56,40,max(head_frame-6,0)*56+56))
    from TrueTerrariaGenerator import BACK_HAIR
    hair_dx = -2 if c['hair']==165 else 0
    hair_dy = -2 if c['hair']==164 and not alt else 0
    if c['hair'] in BACK_HAIR and show_hair:
        paste(hair,hair_dx,hair_dy,c['hair_color'],part='head')
    hx,hy=0,0
    if head==270: hx=-10
    elif head==268: hy=-6
    elif head in (222,272) and c['hair'] in (15,76,108): hy=4
    elif head==275: hy=-4
    # Player.GetHelmetOffsetAddonFromFaceHead: skull face accessories displace hats.
    if face_head:
        if head in (16,21,24,65,67,94,95,96,159,222,231,250): hx+=2
        elif head in (59,64,106,138,181,220): hy-=2
        elif head in (26,51,60,81): hx+=2;hy-=2
        elif head==97: hx-=2
        elif head==117: hx-=4
    back=RULES['head']['back_ids'].get(str(head),0)
    accessory('back')
    armor('head',back,y=head_frame,dx=hx,dy=hy)
    balloon(False)
    hide_top=body and in_set('body','HidesTopSkin',body)
    hide_bottom=(body and in_set('body','HidesBottomSkin',body)) or (legs and in_set('legs','HidesBottomSkin',legs))
    if not hide_top: player(3,'skin_color',tx,ty)
    shoe_overrides=selected.get('shoes',0) and in_set('shoe','OverridesLegs',selected['shoes'])
    pants_override=in_set('legs','OverridesLegs',legs)
    if not hide_bottom and not shoe_overrides and not pants_override: player(10,'skin_color',y=leg_frame,composite=False)
    arms=not body or not in_set('body','HidesArms',body)
    hands=not body or not in_set('body','HidesHands',body)
    shoulders=frame!=5 or not body or in_set('body','showsShouldersWhileJumping',body)
    if body:
        if not hide_top and arms:
            player(7,'skin_color',bx,by); player(5,'skin_color',bx,by)
        if shoulders: armor('body',body,1,3 if female else 1,dy=bob)
        balloon(True)
        armor('body',body,bx,by,dy=bob)
        if not hide_top and hands and not arms:
            player(5,'skin_color',bx,by)
    else:
        for p,t in [(7,'skin_color'),(5,'skin_color'),(8,'undershirt_color'),(13,'shirt_color')]: player(p,t,bx,by)
        balloon(True)
    accessory('hand_off',x=bx,row=by,dy=bob,arm='back')
    if legs and (not shoe_overrides or body in ROBES):
        if legs==140:
            src=g._open(g.assets_path/'Armor/Legs/Extra_73.png')
            # DrawPlayer_13_Leggings: standing column x=18, airborne column x=0.
            sy=effect_frame%8*26
            sx=0 if leg_frame==1 else 18
            paste(dyed(src.crop((sx,sy,sx+16,sy+24)),armor_dyes.get(leg_dye_slot,'#ffffff')),12,42+bob,part='legs')
        elif legs!=169: armor('legs',legs,y=leg_frame,dx=-6 if legs==226 else 0)
    elif not shoe_overrides:
        player(11,'pants_color',y=leg_frame,variant=c['pants_variant'],composite=False)
        player(12,'shoes_color',y=leg_frame,variant=c['shoes_variant'],composite=False)
    if not in_set('legs','OverridesLegs',legs): accessory('shoes',row=leg_frame)
    if not body and c['skin_variant'] in (3,7,8): player(14,'shirt_color',y=leg_frame,composite=False)
    if body in COATS: armor('legs',gender(COATS[body],female),y=leg_frame,dye_slot='body')
    if body: armor('body',body,tx,ty,dy=bob)
    else:
        for x,y in [(1,3 if female else 1),(tx,ty)]:
            player(4,'undershirt_color',x,y); player(6,'shirt_color',x,y)
    accessory('waist',row=frame if in_set('waist','UsesTorsoFraming',selected.get('waist',0)) else leg_frame)
    accessory('neck')
    if face_head and in_set('head','DrawHead',head):
        face_id=RULES['face']['mappings']['AltFaceHead'].get(str(face),face) if in_set('head','UseAltFaceHeadDraw',head) else face
        accessory('face',face_id,row=head_frame,dx=2 if head==196 else 0,dy=-2 if head in (20,221) else 0)
    elif in_set('head','DrawHead',head):
        player(0,'skin_color',y=head_frame,composite=False)
        src=g._open(g.player_path/g.texture_name(c['skin_variant'],1))
        paste(src.crop((0,eye_frame*56,40,eye_frame*56+56)),part='head')
        player(2,'eye_color',y=eye_frame,composite=False)
    if face and in_set('face','DrawInFaceUnderHairLayer',face): accessory('face',row=head_frame)
    head_tint=c['skin_color'] if in_set('head','UseSkinColor',head) else None
    if full and not hide_helmet: armor('head',head,y=head_frame,dx=hx,dy=hy,tint=head_tint)
    if show_hair and head!=259:
        paste(hair.crop((0,0,40,26)) if c['hair'] in BACK_HAIR else hair,hair_dx,hair_dy,c['hair_color'],part='head')
    if hide_helmet: pass
    elif head==259:
        # One stacked rabbit hat, neutral independent animation frame (46x40).
        armor('head',head,width=46,height=40,sy=0,dx=-2,dy=bob-16)
        paste(hair.crop((0,0,40,26)) if c['hair'] in BACK_HAIR else hair,hair_dx,hair_dy,c['hair_color'],part='head')
    elif head==265:
        # One badger hat is six stacked 20x10 slices; use neutral sway/time.
        for i in range(5,-1,-1):
            row=0 if i==5 else 5 if i==0 else (4-i)%4+1
            armor('head',head,width=20,height=10,sy=row*10,dx=10,dy=16+bob-4*i+(2 if i==5 else 0))
    elif head==270:
        # The source uses a 42px rectangle and an asymmetric horizontal offset.
        armor('head',head,y=head_frame,dx=hx,dy=hy,width=42)
    elif head and head!=28:
        tall=in_set('head','IsTallHat',head)
        adjust=2 if tall and head_frame else 0
        armor('head',head,sy=head_frame*56-adjust,dx=hx,dy=hy-adjust,height=48 if tall else 52,tint=head_tint)
    if not in_set('head','PreventBeardDraw',head):
        beard=selected.get('beard',0)
        accessory('beard',row=head_frame,tint=c['hair_color'] if in_set('beard','UseHairColor',beard) else None,
                  dx=8 if head==165 else 2 if head in (146,148,150,152) else 0)
    if face and not face_head and not in_set('face','DrawInFaceUnderHairLayer',face):
        flower=in_set('face','DrawInFaceFlowerLayer',face)
        accessory('face',row=head_frame,dx=hx if flower else 0,dy=-6 if face==19 else hy if flower else 0)
    front_in_neck_layer=frame==5 and in_set('front','DrawsInNeckLayer',selected.get('front',0))
    if front_in_neck_layer:front_accessory(True)
    front_accessory(False)
    accessory('shield')
    shoulder=(0,3 if female else 1)
    over=frame not in (1,2,5) and (not body or not in_set('body','shouldersAreAlwaysInTheBack',body))
    for part in (('arm','shoulder') if over else ('shoulder','arm')):
        if body:
            if part=='arm':
                if not hide_top:
                    if arms: player(7,'skin_color',fx,fy)
                    if hands: player(9,'skin_color',fx,fy)
                armor('body',body,fx,fy,dy=bob)
            elif shoulders: armor('body',body,*shoulder,dx=shoulder_offset(body,frame),dy=bob)
        else:
            x,y=(fx,fy) if part=='arm' else shoulder
            for p,t in [(7,'skin_color'),(8,'undershirt_color'),(13,'shirt_color'),(6,'shirt_color')]: player(p,t,x,y)
    accessory('hand_on',x=fx,row=fy,dy=bob,arm='front')
    if not front_in_neck_layer:front_accessory(True)
    from transforms import render_layers
    return render_layers(layers,pose,direction,bob,96 if legs==140 else 80)
