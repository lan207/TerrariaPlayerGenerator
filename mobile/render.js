/* Pixel-exact nearest-neighbour affine rendering, shared coordinate conventions
 * with transforms.py. Each layer is sampled once after composing its transforms. */
'use strict';
window.AdvancedPlayer = ({canvas,load,texture,basic}) => {
  const cat=OFFLINE_CATALOG, identity=[1,0,0,1,0,0];
  const mul=([A,B,C,D,E,F],[a,b,c,d,e,f])=>[A*a+C*b,B*a+D*b,A*c+C*d,B*c+D*d,A*e+C*f+E,B*e+D*f+F];
  function rotate(v={},[x,y]){const t=(v.angle||0)*Math.PI/180,c=+Math.cos(t).toFixed(14),s=+Math.sin(t).toFixed(14);return [c,s,-s,c,x-c*x+s*y+(v.x||0),y-s*x-c*y+(v.y||0)];}
  function matrix(pose,part,arm,bob,direction){
    let m=identity;const data=pose?.[arm+'_arm'];
    if(data?.enabled){m=rotate(data,arm==='front'?[27,52+bob]:[38,54+bob]);if(arm==='front')m=mul([1,0,0,1,1,1],m);}
    m=mul(rotate(pose?.[part+'_transform'],{head:[32,42],body:[32,52],legs:[32,64]}[part]),m);
    if(direction===-1)m=mul([-1,0,0,1,64,0],m);
    return mul(rotate(pose?.whole_transform,[32,52]),m);
  }
  function normalize(raw={}){
    const pose=structuredClone(cat.sequence.default_pose);
    for(const key of Object.keys(raw)){if(!(key in pose))throw Error('自定义姿势包含未知字段');pose[key]=typeof pose[key]==='object'?{...pose[key],...raw[key]}:raw[key];}
    const number=(n,lo,hi,integer=false)=>{if(typeof n!=='number'||!Number.isFinite(n)||n<lo||n>hi||integer&&!Number.isInteger(n))throw Error('无效的姿势参数');};
    for(const key of ['body_frame','head_frame','leg_frame'])number(pose[key],0,19,true);
    number(pose.effect_frame,0,7,true);if(![-1,1].includes(pose.direction))throw Error('无效的朝向');
    for(const part of ['head','body','legs','whole']){const v=pose[part+'_transform'];for(const key of Object.keys(v))if(!['angle','x','y'].includes(key))throw Error('无效的部位变换');number(v.angle,-180,180);number(v.x,-128,128);number(v.y,-128,128);}
    for(const side of ['front','back']){const v=pose[side+'_arm'];if(typeof v.enabled!=='boolean'||!(v.stretch in cat.sequence.stretches))throw Error('无效的手臂参数');number(v.angle,-180,180);}
    return pose;
  }
  function shooting(angle){
    if(typeof angle!=='number'||!Number.isFinite(angle)||Math.abs(angle)>180)throw Error('无效的瞄准角度');
    const p=normalize(),a=angle*Math.PI/180,e=Math.atan2(Math.sin(a),Math.abs(Math.cos(a))),f=e<-.75?2:e>.6?4:3;
    p.body_frame=f;p.head_frame=f;p.direction=Math.abs(angle)<=90?1:-1;p.front_arm.enabled=p.back_arm.enabled=false;return p;
  }
  async function compose(c,action='idle',index=0,raw=null){
    c={...cat.defaults,...c,_action:action};
    const frames=action==='use'?cat.use_frames[c.use_style]:cat.frames[action];
    if(!frames||!Number.isInteger(index)||index<0||index>=frames.length)throw Error('无效的动作帧');
    let pose=raw?normalize(raw):action==='shoot'?shooting(c.aim_angle||0):structuredClone(cat.builtin_poses[action]?.[index]||null);
    if(pose&&!raw&&action!=='shoot')pose.direction=c.direction;
    if(!pose&&!c.armor_head&&!c.armor_body&&!c.armor_legs&&!Object.values(c.accessories||{}).some(Boolean))return basic(c,action,index);
    const plan=EquipmentLayers(c,pose,frames[index],index,texture);
    let left=0,top=0,right=64,bottom=plan.height;
    const layers=[];
    for(const layer of plan.layers){
      const src=await load(layer.path),w=layer.width??src.width,h=layer.height;
      const pixels=new Uint8ClampedArray(w*h*4),colors=layer.colors.map(color=>[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)));
      let x0=w,y0=h,x1=0,y1=0;
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){
        const sx=x+layer.sx,sy=y+layer.sy;if(sx<0||sy<0||sx>=src.width||sy>=src.height)continue;
        const i=(y*w+x)*4,s=(sy*src.width+sx)*4;if(!src.pixels[s+3])continue;
        pixels.set(src.pixels.subarray(s,s+4),i);
        for(const rgb of colors)for(let k=0;k<3;k++)pixels[i+k]=Math.round(pixels[i+k]*rgb[k]/255);
        x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x+1);y1=Math.max(y1,y+1);
      }
      if(!x1||!y1)continue;
      const m=mul(matrix(pose,layer.part,layer.arm,plan.bob,plan.direction),[1,0,0,1,layer.dx,layer.dy]);
      const [a,b,c,d,e,f]=m,points=[];for(const x of [x0,x1])for(const y of [y0,y1])points.push([a*x+c*y+e,b*x+d*y+f]);
      const box=[Math.floor(Math.min(...points.map(p=>p[0]))),Math.floor(Math.min(...points.map(p=>p[1]))),Math.ceil(Math.max(...points.map(p=>p[0]))),Math.ceil(Math.max(...points.map(p=>p[1])))];
      left=Math.min(left,box[0]);top=Math.min(top,box[1]);right=Math.max(right,box[2]);bottom=Math.max(bottom,box[3]);
      layers.push({pixels,w,h,m,box});
    }
    const transformed=pose&&(['head','body','legs','whole'].some(part=>['angle','x','y'].some(k=>pose[part+'_transform']?.[k]))||['front','back'].some(s=>pose[s+'_arm'].angle));
    if(!transformed){left=0;top=0;right=64;bottom=plan.height;}
    const out=canvas(right-left,bottom-top),data=new Uint8ClampedArray(out.width*out.height*4);
    for(const {pixels,w,h,m:[a,b,c,d,e,f],box} of layers){
      const det=a*d-b*c;
      for(let y=Math.max(top,box[1]);y<Math.min(bottom,box[3]);y++)for(let x=Math.max(left,box[0]);x<Math.min(right,box[2]);x++){
        const px=x+.5-e,py=y+.5-f,sx=Math.floor((d*px-c*py)/det),sy=Math.floor((-b*px+a*py)/det);
        if(sx<0||sy<0||sx>=w||sy>=h)continue;
        const s=(sy*w+sx)*4,alpha=pixels[s+3];if(!alpha)continue;
        const i=((y-top)*out.width+x-left)*4,total=alpha+data[i+3]*(255-alpha)/255;
        for(let k=0;k<3;k++)data[i+k]=Math.round((pixels[s+k]*alpha+data[i+k]*data[i+3]*(255-alpha)/255)/total);
        data[i+3]=Math.round(total);
      }
    }
    out.getContext('2d').putImageData(new ImageData(data,out.width,out.height),0,0);out.origin=[left,top];return out;
  }
  async function sequence(c,entries){
    if(!Array.isArray(entries)||!entries.length||entries.length>120)throw Error('时间轴需要 1–120 帧');
    const images=[];
    for(const e of entries){
      if(!Number.isInteger(e.duration)||e.duration<20||e.duration>2000||e.duration%10)throw Error('无效的帧时长');
      let im;
      if(e.kind==='custom')im=await compose(c,'idle',0,e.pose);
      else if(e.kind==='fixed')im=await compose(e.action==='shoot'?{...c,aim_angle:e.aim_angle||0}:c,e.action,e.frame);
      else throw Error('无效的帧类型');
      if(im.width===40&&im.height===56){const padded=canvas(64,80);padded.getContext('2d').drawImage(im,12,24);im=padded;}
      images.push(im);
    }
    const left=Math.min(...images.map(im=>im.origin?.[0]||0)),top=Math.min(...images.map(im=>im.origin?.[1]||0));
    const right=Math.max(...images.map(im=>(im.origin?.[0]||0)+im.width)),bottom=Math.max(...images.map(im=>(im.origin?.[1]||0)+im.height));
    return images.map(im=>{const out=canvas(right-left,bottom-top);out.getContext('2d').drawImage(im,(im.origin?.[0]||0)-left,(im.origin?.[1]||0)-top);out.origin=[left,top];return out;});
  }
  return {compose,sequence};
};
