/* Offline layer planner. Keep ordering and ownership in sync with equipment.py. */
'use strict';
window.EquipmentLayers = (c, pose, frame, index, texture) => {
  c={...c,_white:'#ffffff'};
  const r=OFFLINE_CATALOG.rules, maps=OFFLINE_CATALOG.equipment_maps;
  const female=[4,5,6,7,9].includes(c.skin_variant), gender=v=>Array.isArray(v)?v[+female]:v;
  const has=(slot,name,n)=>r[slot].sets[name].default!==r[slot].sets[name].exceptions.includes(n);
  let head=c.armor_head||0,body=c.armor_body||0,legs=c.armor_legs||0;
  if(head===201&&female)head=202;
  if(maps.ROBES[body])legs=gender(maps.ROBES[body]);else if(body===81&&!legs)legs=169;
  legs=gender(maps.LEG_MATCH[legs]||legs);
  const selected={...c.accessories}, raw=c.accessories||{};
  if(maps.CAPE_BACK_TO_FRONT[selected.back]&&!selected.front)selected.front=maps.CAPE_BACK_TO_FRONT[selected.back];
  else if(maps.CAPE_FRONT_TO_BACK[selected.front]&&!selected.back)selected.back=maps.CAPE_FRONT_TO_BACK[selected.front];
  if(c.auto_capes!==false){
    let back=r.body.mappings[female?'IncludedCapeBackFemale':'IncludedCapeBack'][body]||0,front=r.body.mappings.IncludedCapeFront[body]||0;
    if([85,235,236].includes(body)&&!selected.front&&!selected.back)[back,front]=({85:[20,7],235:[30,9],236:[31,10]})[body];
    if(back&&!selected.back)selected.back=back;if(front&&!selected.front)selected.front=front;
  }
  if(body&&has('body','DisableHandOnAndOffAccDraw',body)){delete selected.hand_on;delete selected.hand_off;}
  if(body&&has('body','DisableBeltAccDraw',body)&&has('waist','IsABelt',selected.waist||0))delete selected.waist;
  const ad=c.armor_dyes||{}, ac=c.accessory_dyes||{};
  function accColor(slot){
    if(ac[slot])return ac[slot];
    const opposite=slot==='front'?'back':'front',pairs=slot==='front'?maps.CAPE_BACK_TO_FRONT:maps.CAPE_FRONT_TO_BACK;
    if(['front','back'].includes(slot)&&selected[slot]&&!raw[slot])return pairs[raw[opposite]]===selected[slot]?(ac[opposite]||'#ffffff'):(ad.body||'#ffffff');
    return '#ffffff';
  }
  const legDye=maps.ROBES[body]||body===81&&!c.armor_legs?'body':'legs';
  let hf=frame,lf=['walk','jump'].includes(c._action)?frame:0;
  if(pose){frame=pose.body_frame;hf=pose.head_frame;lf=pose.leg_frame;}
  const cells=[[2,0],[3,0],[4,0],[5,0],[6,0],[2,1],[3,1],[4,1],[4,1],[4,1],[4,1],[3,1],[3,1],[3,1],[5,1],[6,1],[6,1],[5,1],[3,1],[3,1]];
  let [fx,fy]=cells[frame],bx=fx,by=fy+2;
  const rows={full:0,three_quarters:1,quarter:2,none:3};
  if(pose?.front_arm.enabled){fx=7;fy=rows[pose.front_arm.stretch];}
  if(pose?.back_arm.enabled){bx=8;by=rows[pose.back_arm.stretch];}
  const tx=+(frame===5),ty=female?2:0,bob=[7,8,9,14,15,16].includes(frame)?-2:0;
  const effect=pose?pose.effect_frame:index,layers=[];
  function paste(path,sx=0,sy=0,width=40,height=56,dx=0,dy=0,colors=[],part='body',arm=null){
    layers.push({path,sx,sy,width,height,dx:dx+12,dy:dy+24,colors:colors.filter(Boolean),part,arm});
  }
  const armAt=(x,y)=>x===fx&&y===fy?'front':x===bx&&y===by?'back':null;
  function player(piece,color,x=0,y=0,variant=c.skin_variant,composite=true){
    paste('Player/'+texture(variant,piece),x*40,y*56,40,56,0,composite?bob:0,[c[color]],
      [0,1,2].includes(piece)?'head':[10,11,12,14].includes(piece)?'legs':'body',composite?armAt(x,y):null);
  }
  function armor(slot,n,x=0,y=0,dx=0,dy=0,width=40,height=56,sy=y*56,tint=null,dyeSlot=null){
    if(!n)return;
    const folder={head:'Head',body:'Body',legs:'Legs'}[slot],prefix={head:'Armor_Head_',body:'Armor_',legs:'Armor_Legs_'}[slot];
    paste(`Armor/${folder}/${prefix}${n}.png`,x*40,sy,width,height,dx,dy,[tint,ad[dyeSlot||(slot==='legs'?legDye:slot)]],dyeSlot==='body'?'body':slot,slot==='body'?armAt(x,y):null);
  }
  function acc(slot,n=selected[slot],x=0,row=frame,dx=0,dy=0,arm=null,tint=null){
    if(!n)return;
    const prefix=maps.accessory_slots[slot][0];
    paste(`Accessories/Acc_${prefix}_${n}.png`,x*40,row*56,slot==='shield'?null:40,56,dx,dy,[tint,accColor(slot)],['face','beard'].includes(slot)?'head':slot==='shoes'?'legs':'body',arm);
  }
  function balloon(front){
    const n=selected.balloon;if(!n||has('balloon','DrawInFrontOfBackArmLayer',n)!==front)return;
    if(has('balloon','UsesTorsoFraming',n)){acc('balloon');return;}
    const [x,y]=maps.OFFHAND[frame];paste(`Accessories/Acc_Balloon_${n}.png`,0,effect%4*56,null,56,x-20,y-24,[accColor('balloon')]);
  }
  function frontAcc(front){const n=selected.front;if(n){const x=front?0:20;paste(`Accessories/Acc_Front_${n}.png`,x,frame*56,20,56,x,0,[accColor('front')]);}}
  const full=has('head','DrawFullHair',head),hat=has('head','DrawHatHair',head),face=selected.face||0;
  const faceHead=face&&has('face','DrawInFaceHeadLayer',face),hideHelmet=face&&has('face','OverrideHelmet',face);
  let showHair=full||hat||!head||head===259;
  if(face&&(has('face','PreventHairDraw',face)||faceHead&&head))showHair=false;
  const alt=head?hat:c.alt_hair, hairPath=`Hair/Player_Hair${alt?'Alt':''}_${c.hair}.png`,hairDx=c.hair===165?-2:0,hairDy=c.hair===164&&!alt?-2:0;
  const backHair=OFFLINE_CATALOG.back_hair.includes(c.hair);
  const hair=(height=56)=>paste(hairPath,0,Math.max(hf-6,0)*56,40,height,hairDx,hairDy,[c.hair_color],'head');
  if(backHair&&showHair)hair();
  let hx=head===270?-10:0,hy=head===268?-6:[222,272].includes(head)&&[15,76,108].includes(c.hair)?4:head===275?-4:0;
  if(faceHead){
    if([16,21,24,65,67,94,95,96,159,222,231,250].includes(head))hx+=2;
    else if([59,64,106,138,181,220].includes(head))hy-=2;
    else if([26,51,60,81].includes(head)){hx+=2;hy-=2;}
    else if(head===97)hx-=2;else if(head===117)hx-=4;
  }
  acc('back');armor('head',r.head.back_ids[head],0,hf,hx,hy);balloon(false);
  const hideTop=body&&has('body','HidesTopSkin',body),hideBottom=body&&has('body','HidesBottomSkin',body)||legs&&has('legs','HidesBottomSkin',legs);
  if(!hideTop)player(3,'skin_color',tx,ty);
  const shoeOverride=selected.shoes&&has('shoe','OverridesLegs',selected.shoes),pantsOverride=has('legs','OverridesLegs',legs);
  if(!hideBottom&&!shoeOverride&&!pantsOverride)player(10,'skin_color',0,lf,c.skin_variant,false);
  const arms=!body||!has('body','HidesArms',body),hands=!body||!has('body','HidesHands',body),shoulders=frame!==5||!body||has('body','showsShouldersWhileJumping',body);
  if(body){
    if(!hideTop&&arms){player(7,'skin_color',bx,by);player(5,'skin_color',bx,by);}
    if(shoulders)armor('body',body,1,female?3:1,0,bob);
    balloon(true);armor('body',body,bx,by,0,bob);
    if(!hideTop&&hands&&!arms)player(5,'skin_color',bx,by);
  }else{for(const [p,t] of [[7,'skin_color'],[5,'skin_color'],[8,'undershirt_color'],[13,'shirt_color']])player(p,t,bx,by);balloon(true);}
  acc('hand_off',undefined,bx,by,0,bob,'back');
  if(legs&&(!shoeOverride||maps.ROBES[body])){
    if(legs===140)paste('Armor/Legs/Extra_73.png',lf===1?0:18,effect%8*26,16,24,12,42+bob,[ad[legDye]],'legs');
    else if(legs!==169)armor('legs',legs,0,lf,legs===226?-6:0);
  }else if(!shoeOverride){player(11,'pants_color',0,lf,c.pants_variant,false);player(12,'shoes_color',0,lf,c.shoes_variant,false);}
  if(!has('legs','OverridesLegs',legs))acc('shoes',undefined,0,lf);
  if(!body&&[3,7,8].includes(c.skin_variant))player(14,'shirt_color',0,lf,c.skin_variant,false);
  if(maps.COATS[body])armor('legs',gender(maps.COATS[body]),0,lf,0,0,40,56,lf*56,null,'body');
  if(body)armor('body',body,tx,ty,0,bob);else for(const [x,y] of [[1,female?3:1],[tx,ty]]){player(4,'undershirt_color',x,y);player(6,'shirt_color',x,y);}
  acc('waist',undefined,0,has('waist','UsesTorsoFraming',selected.waist||0)?frame:lf);acc('neck');
  if(faceHead&&has('head','DrawHead',head))acc('face',has('head','UseAltFaceHeadDraw',head)?r.face.mappings.AltFaceHead[face]||face:face,0,hf,head===196?2:0,[20,221].includes(head)?-2:0);
  else if(has('head','DrawHead',head)){player(0,'skin_color',0,hf,c.skin_variant,false);player(1,'_white',0,hf,c.skin_variant,false);player(2,'eye_color',0,hf,c.skin_variant,false);}
  if(face&&has('face','DrawInFaceUnderHairLayer',face))acc('face',undefined,0,hf);
  const headTint=has('head','UseSkinColor',head)?c.skin_color:null;
  if(full&&!hideHelmet)armor('head',head,0,hf,hx,hy,40,56,hf*56,headTint);
  if(showHair&&head!==259)hair(backHair?26:56);
  if(!hideHelmet){
    if(head===259){armor('head',head,0,0,-2,bob-16,46,40,0);hair(backHair?26:56);}
    else if(head===265){for(let i=5;i>=0;i--){const row=i===5?0:i===0?5:(4-i)%4+1;armor('head',head,0,0,10,16+bob-4*i+(i===5?2:0),20,10,row*10);}}
    else if(head===270)armor('head',head,0,hf,hx,hy,42);
    else if(head&&head!==28){const tall=has('head','IsTallHat',head),adjust=tall&&hf?2:0;armor('head',head,0,0,hx,hy-adjust,40,tall?48:52,hf*56-adjust,headTint);}
  }
  if(!has('head','PreventBeardDraw',head))acc('beard',undefined,0,hf,head===165?8:[146,148,150,152].includes(head)?2:0,0,null,has('beard','UseHairColor',selected.beard||0)?c.hair_color:null);
  if(face&&!faceHead&&!has('face','DrawInFaceUnderHairLayer',face)){const flower=has('face','DrawInFaceFlowerLayer',face);acc('face',undefined,0,hf,flower?hx:0,face===19?-6:flower?hy:0);}
  const frontNeck=frame===5&&has('front','DrawsInNeckLayer',selected.front||0);
  if(frontNeck)frontAcc(true);frontAcc(false);acc('shield');
  const over=![1,2,5].includes(frame)&&(!body||!has('body','shouldersAreAlwaysInTheBack',body));
  for(const part of (over?['arm','shoulder']:['shoulder','arm'])){
    if(body){
      if(part==='arm'){if(!hideTop){if(arms)player(7,'skin_color',fx,fy);if(hands)player(9,'skin_color',fx,fy);}armor('body',body,fx,fy,0,bob);}
      else if(shoulders)armor('body',body,0,female?3:1,maps.shoulder_offsets[body]?.[frame]||0,bob);
    }else{const [x,y]=part==='arm'?[fx,fy]:[0,female?3:1];for(const [p,t] of [[7,'skin_color'],[8,'undershirt_color'],[13,'shirt_color'],[6,'shirt_color']])player(p,t,x,y);}
  }
  acc('hand_on',undefined,fx,fy,0,bob,'front');if(!frontNeck)frontAcc(true);
  const equipment={head:head?[`Armor_Head_${head}.png`]:[],body:body?[`Armor_${body}.png`]:[],legs:legs?[`Armor_Legs_${legs}.png`]:[]};
  if(r.head.back_ids[head])equipment.head.push(`Armor_Head_${r.head.back_ids[head]}.png`);
  if(maps.COATS[body])equipment.body.push(`Armor_Legs_${gender(maps.COATS[body])}.png`);
  if(legs===140)equipment.legs=['Extra_73.png'];
  const accessoryTextures={},dyeSources={};
  for(const [slot,n] of Object.entries(selected))if(n){
    accessoryTextures[slot]=`Acc_${maps.accessory_slots[slot][0]}_${n}.png`;dyeSources[slot]=slot;
    if(['front','back'].includes(slot)&&!raw[slot]){
      const opposite=slot==='front'?'back':'front',pairs=slot==='front'?maps.CAPE_BACK_TO_FRONT:maps.CAPE_FRONT_TO_BACK;
      dyeSources[slot]=pairs[raw[opposite]]===n?opposite:'body';
    }
  }
  return {layers,bob,height:legs===140?96:80,direction:pose?pose.direction:c.direction,
    textures:{hair:[`Player_Hair${alt?'Alt':''}_${c.hair}.png`],skin:[texture(c.skin_variant,0),texture(c.skin_variant,3),texture(c.skin_variant,5),texture(c.skin_variant,7),texture(c.skin_variant,10)],
      eyes:[texture(c.skin_variant,1),texture(c.skin_variant,2)],shirt:[texture(c.skin_variant,6),texture(c.skin_variant,13)],
      undershirt:[texture(c.skin_variant,4),texture(c.skin_variant,8)],pants:[texture(c.pants_variant,11)],shoes:[texture(c.shoes_variant,12)],
      equipment,accessories:accessoryTextures,accessory_dye_sources:dyeSources}};
};
