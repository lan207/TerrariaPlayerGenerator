/* Offline counterpart of TrueTerrariaGenerator.py. No network or Python runtime. */
'use strict';
window.LocalPlayer = (() => {
  const catalog = window.OFFLINE_CATALOG;
  const files = new Set(catalog.player_files), backHair = new Set(catalog.back_hair);
  const cache = new Map();
  const canvas = (w = 40, h = 56) => Object.assign(document.createElement('canvas'), {width:w, height:h});
  function texture(variant, piece) {
    const base = [4,5,6,7,9].includes(variant) ? 4 : 0;
    for (const v of [variant, base, 0]) {
      const name = `Player_${v}_${piece}.png`;
      if (files.has(name)) return name;
    }
    throw new Error(`缺少部位贴图：${variant}/${piece}`);
  }
  async function load(path) {
    if (!cache.has(path)) {
      const promise = new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
          const c = canvas(image.width, image.height), ctx = c.getContext('2d', {willReadFrequently:true});
          ctx.drawImage(image, 0, 0);
          const pixels = ctx.getImageData(0, 0, c.width, c.height);
          resolve({pixels:pixels.data, width:c.width, height:c.height});
        };
        image.onerror = () => reject(new Error(`无法读取本地素材：${path}`));
        image.src = '/Assets/' + path;
      });
      cache.set(path, promise);
      promise.catch(() => cache.delete(path));
      // Keep memory bounded when browsing all 330 hair sheets.
      if (cache.size > 48) cache.delete(cache.keys().next().value);
    }
    return cache.get(path);
  }
  function frames(action, style) {
    return action==='use'?catalog.use_frames[style]:catalog.frames[action];
  }
  function names(c) {
    const list = (pieces, v = c.skin_variant) => pieces.map(p => texture(v, p));
    return {hair:[`Player_Hair${c.alt_hair ? 'Alt' : ''}_${c.hair}.png`],
      skin:list([0,3,5,7,10]), eyes:list([1,2]),
      shirt:list([6,13,...([3,7,8].includes(c.skin_variant) ? [14] : [])]),
      undershirt:list([4,8]), pants:list([11],c.pants_variant), shoes:list([12],c.shoes_variant),
      ...EquipmentLayers({...c,_action:'idle'},null,0,0,texture).textures};
  }
  async function composeLegacy(c, action = 'idle', index = 0) {
    const body = frames(action, c.use_style)[index];
    const female = [4,5,6,7,9].includes(c.skin_variant);
    const armCells = [[2,0],[3,0],[4,0],[5,0],[6,0],[2,1],[3,1],[4,1],[4,1],[4,1],
      [4,1],[3,1],[3,1],[3,1],[5,1],[6,1],[6,1],[5,1],[3,1],[3,1]];
    const [fx, fy] = armCells[body], tx = body === 5 ? 1 : 0, ty = female ? 2 : 0;
    const bob = [7,8,9,14,15,16].includes(body) ? -2 : 0;
    const leg = ['walk','jump'].includes(action) ? body : 0;
    const layers = [];
    const draw = (piece, color, x = 0, y = 0, variant = c.skin_variant, composite = true) =>
      layers.push({path:'Player/'+texture(variant,piece), color, sx:x*40, sy:y*56, dx:0, dy:composite ? bob : 0, height:56});
    const hair = {path:`Hair/Player_Hair${c.alt_hair ? 'Alt' : ''}_${c.hair}.png`, color:c.hair_color,
      sx:0, sy:Math.max(body-6,0)*56, dx:c.hair === 165 ? -2 : 0,
      dy:c.hair === 164 && !c.alt_hair ? -2 : 0, height:56};
    if (backHair.has(c.hair)) layers.push(hair);
    draw(3,c.skin_color,tx,ty);
    draw(10,c.skin_color,0,leg,c.skin_variant,false);
    for (const [p,t] of [[7,c.skin_color],[5,c.skin_color],[8,c.undershirt_color],[13,c.shirt_color]]) draw(p,t,fx,fy+2);
    draw(11,c.pants_color,0,leg,c.pants_variant,false);
    draw(12,c.shoes_color,0,leg,c.shoes_variant,false);
    if ([3,7,8].includes(c.skin_variant)) draw(14,c.shirt_color,0,leg,c.skin_variant,false);
    for (const [x,y] of [[1,female ? 3 : 1],[tx,ty]]) {
      draw(4,c.undershirt_color,x,y); draw(6,c.shirt_color,x,y);
    }
    draw(0,c.skin_color,0,body,c.skin_variant,false);
    draw(1,'#ffffff',0,body,c.skin_variant,false);
    draw(2,c.eye_color,0,body,c.skin_variant,false);
    layers.push({...hair, height:backHair.has(c.hair) ? 26 : 56});
    const shoulder = [0,female ? 3 : 1], arm = [fx,fy];
    for (const [x,y] of ([1,2,5].includes(body) ? [shoulder,arm] : [arm,shoulder]))
      for (const [p,t] of [[7,c.skin_color],[8,c.undershirt_color],[13,c.shirt_color],[6,c.shirt_color]]) draw(p,t,x,y);
    const sources = await Promise.all(layers.map(l => load(l.path)));
    const out = new Uint8ClampedArray(40*56*4);
    layers.forEach((l, n) => {
      const src = sources[n], rgb = [1,3,5].map(i => parseInt(l.color.slice(i,i+2),16));
      for (let y = 0; y < l.height; y++) for (let x = 0; x < 40; x++) {
        const dx=x+l.dx, dy=y+l.dy, sx=x+l.sx, sy=y+l.sy;
        if (dx<0 || dx>=40 || dy<0 || dy>=56 || sx>=src.width || sy>=src.height) continue;
        const s=(sy*src.width+sx)*4, d=(dy*40+dx)*4, a=src.pixels[s+3];
        if (!a) continue;
        const alpha=a+out[d+3]*(255-a)/255;
        for (let k=0;k<3;k++) out[d+k]=Math.round((Math.round(src.pixels[s+k]*rgb[k]/255)*a + out[d+k]*out[d+3]*(255-a)/255)/alpha);
        out[d+3]=Math.round(alpha);
      }
    });
    const c2 = canvas(), ctx=c2.getContext('2d');
    if (c.direction === -1) {
      const flipped = new Uint8ClampedArray(out.length);
      for (let y=0;y<56;y++) for(let x=0;x<40;x++) flipped.set(out.subarray((y*40+x)*4,(y*40+x)*4+4),(y*40+39-x)*4);
      ctx.putImageData(new ImageData(flipped,40,56),0,0);
    } else ctx.putImageData(new ImageData(out,40,56),0,0);
    return c2;
  }
  const advanced = window.AdvancedPlayer({canvas,load,texture,basic:composeLegacy});
  async function compose(c, action = 'idle', index = 0, pose = null) {
    return advanced.compose(c,action,index,pose);
  }
  async function render(c, action) {
    const result=[];
    for (let i=0;i<frames(action,c.use_style).length;i++) {
      result.push(await compose(c,action,i));
      await new Promise(resolve => setTimeout(resolve,0));
    }
    return result;
  }
  function sheet(list, scale) {
    const {width,height}=list[0];
    const c=canvas(width*list.length*scale,height*scale), ctx=c.getContext('2d');
    ctx.imageSmoothingEnabled=false;
    list.forEach((im,i)=>ctx.drawImage(im,i*width*scale,0,width*scale,height*scale));
    return c;
  }
  // GIF89a, shared palette, transparent index 255, disposal 2 and infinite loop.
  // Reset LZW every 200 literals to keep codes at 9 bits; small sprites need no dependency.
  function gif(list, interval, scale) {
    const {width,height}=list[0];
    const pixels=list.map(c=>c.getContext('2d').getImageData(0,0,width,height).data);
    const histogram=new Map();
    for (const data of pixels) for(let i=0;i<data.length;i+=4) if(data[i+3]>=128) {
      const key=(data[i]<<16)|(data[i+1]<<8)|data[i+2]; histogram.set(key,(histogram.get(key)||0)+1);
    }
    const palette=[...histogram].sort((a,b)=>b[1]-a[1]).slice(0,255).map(([k])=>[k>>16,(k>>8)&255,k&255]);
    const mapped=new Map();
    for(const key of histogram.keys()) {
      const rgb=[key>>16,(key>>8)&255,key&255]; let best=0, dist=Infinity;
      palette.forEach((p,i)=>{const d=p.reduce((sum,v,k)=>sum+(v-rgb[k])**2,0); if(d<dist){best=i;dist=d;}});
      mapped.set(key,best);
    }
    const output=[], byte=v=>output.push(v&255), word=v=>{byte(v);byte(v>>8);};
    const str=s=>{for(const c of s) byte(c.charCodeAt(0));};
    str('GIF89a'); word(width*scale); word(height*scale); byte(0xf7); byte(255); byte(0);
    for(let i=0;i<256;i++) for(const v of (palette[i]||[0,0,0])) byte(v);
    byte(0x21);byte(0xff);byte(11);str('NETSCAPE2.0');byte(3);byte(1);word(0);byte(0);
    for(const [frameIndex,data] of pixels.entries()) {
      byte(0x21);byte(0xf9);byte(4);byte(9);word(Math.round((Array.isArray(interval)?interval[frameIndex]:interval)/10));byte(255);byte(0);
      byte(0x2c);word(0);word(0);word(width*scale);word(height*scale);byte(0);byte(8);
      const packed=[];let bits=0, count=0, literals=0;
      const code=v=>{bits|=v<<count;count+=9;while(count>=8){packed.push(bits&255);bits>>>=8;count-=8;}};
      code(256);
      for(let y=0;y<height*scale;y++) for(let x=0;x<width*scale;x++) {
        if(literals===200){code(256);literals=0;}
        const i=(Math.floor(y/scale)*width+Math.floor(x/scale))*4;
        code(data[i+3]<128 ? 255 : mapped.get((data[i]<<16)|(data[i+1]<<8)|data[i+2]));literals++;
      }
      code(257);if(count)packed.push(bits&255);
      for(let i=0;i<packed.length;i+=255){byte(Math.min(255,packed.length-i));for(const v of packed.slice(i,i+255))byte(v);}
      byte(0);
    }
    byte(0x3b);return new Blob([new Uint8Array(output)],{type:'image/gif'});
  }
  async function request(path, body, signal) {
    const check=()=>{if(signal?.aborted)throw new DOMException('已取消','AbortError');};
    check();const c=structuredClone(body.config);
    let result;
    if(path==='/api/preview') {
      const plan=EquipmentLayers({...c,_action:'idle'},null,0,0,texture),im=await compose(c);
      result={image:im.toDataURL(),width:im.width,height:im.height,textures:plan.textures};
    }
    else if(path==='/api/generate') {
      const animations={},sizes={};
      for(const action of Object.keys(catalog.actions)) {
        check();const images=await render(c,action);animations[action]=images.map(im=>im.toDataURL());sizes[action]=[images[0].width,images[0].height];
      }
      result={animations,sizes,width:sizes.idle[0],height:sizes.idle[1]};
    } else if(path==='/api/sequence'||path==='/api/action') {
      const list=path==='/api/sequence'?await advanced.sequence(c,body.sequence):await render(c,body.action);
      result={images:list.map(im=>im.toDataURL()),width:list[0].width,height:list[0].height};
    } else if(path==='/api/export') {
      if(!['gif','frame','sheet'].includes(body.kind)||!Number.isInteger(body.scale)||body.scale<1||body.scale>8)throw Error('无效的导出设置');
      const list=body.action==='custom'?await advanced.sequence(c,body.sequence):await render(c,body.action);
      const count=body.kind==='frame'?1:list.length,w=list[0].width,h=list[0].height;
      if(w*h*body.scale**2*count>40000000||w*body.scale*(body.kind==='sheet'?count:1)>32767||h*body.scale>32767)throw Error('导出尺寸过大，请降低倍率或减少帧数');
      if(!Number.isInteger(body.frame)||body.frame<0||body.frame>=list.length)throw Error('无效的当前帧');
      const duration=body.action==='custom'?body.sequence.map(e=>e.duration):body.interval;
      const blob=body.kind==='gif' ? gif(list,duration,body.scale) :
        await new Promise((resolve,reject)=>sheet(body.kind==='frame' ? [list[body.frame]] : list,body.scale).toBlob(blob=>blob?resolve(blob):reject(Error('画布过大，无法导出 PNG')),'image/png'));
      check();return new Response(blob);
    } else throw new Error('未知本地操作');
    check();return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json'}});
  }
  return {catalog,request,compose,gif,sequence:advanced.sequence};
})();
