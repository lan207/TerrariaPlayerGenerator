'use strict';
window.AimControl=(()=>{
  let enabled=false,pending=false,serial=0,request=null,debounce=null,renderedAngle=0;
  const clamp=value=>Math.max(-180,Math.min(180,Number.isFinite(Number(value))?Number(value):0));
  const angle=()=>Number(config.aim_angle)||0;
  function sync(){
    if(!enabled)return;
    $('#shoot-angle').value=angle();$('#shoot-range').value=angle();
    $('#shoot-state').textContent=pending?'正在更新瞄准…':`单帧 · ${Math.abs(angle())<=90?'朝右':'朝左'} · ${angle().toFixed(1)}°`;
    drawRay();
  }
  function origin(){
    const image=$('#motion-image'),box=image.getBoundingClientRect();
    const width=image.naturalWidth||64,height=image.naturalHeight||80;
    const scale=Math.min(box.width/width,box.height/height);
    // Player.Center relative to the sprite: (20,31), plus the transparent margin.
    return {x:box.left+(box.width-width*scale)/2+(width===40?20:32)*scale,
      y:box.top+(box.height-height*scale)/2+(width===40?31:55)*scale};
  }
  function drawRay(){
    if(!enabled)return;
    const ray=$('#shoot-ray');ray.hidden=action!=='shoot';if(ray.hidden)return;
    const point=origin(),box=$('.motion-preview').getBoundingClientRect();
    ray.style.left=`${point.x-box.left}px`;ray.style.top=`${point.y-box.top}px`;ray.style.transform=`rotate(${angle()}deg)`;
  }
  function invalidate(){serial++;request?.abort();clearTimeout(debounce);pending=false;}
  function ready(){return enabled&&!pending&&snapshot&&renderedAngle===angle()&&!!animations?.shoot;}
  async function render(){
    if(!snapshot||!animations)return;
    const version=serial,appearance=revision,chosenAngle=angle();request=new AbortController();pending=true;sync();
    try{
      const data=await(await api('/api/action',{action:'shoot',config:{...snapshot,aim_angle:chosenAngle}},request.signal)).json();
      if(version!==serial||appearance!==revision||!animations)return;
      animations.shoot=data.images;snapshot.aim_angle=chosenAngle;renderedAngle=chosenAngle;pending=false;
      if(action==='shoot')selectAction('shoot');sync();
    }catch(error){if(error.name==='AbortError'||version!==serial||appearance!==revision)return;
      pending=false;renderedAngle=NaN;$('#shoot-state').textContent='瞄准更新失败，请调整角度重试';toast(error.message,true);}
  }
  function setAngle(value){
    if(!enabled)return;
    const next=clamp(value);
    if(next===angle()&&ready())return;
    config.aim_angle=next;serial++;request?.abort();clearTimeout(debounce);pending=true;stop();
    try{localStorage.setItem('player-studio-config',JSON.stringify(config));}catch(_){}
    sync();if(snapshot)debounce=setTimeout(render,70);
  }
  function init(){
    if(!catalog.aiming)return;enabled=true;
    $('#shoot-angle').onchange=e=>setAngle(e.target.value);
    $('#shoot-range').oninput=e=>setAngle(e.target.value);
    const stage=$('.motion-preview');
    function target(event){
      if(action!=='shoot'||!snapshot)return;
      const point=origin(),dx=event.clientX-point.x,dy=event.clientY-point.y;
      if(dx*dx+dy*dy<9)return;
      setAngle(Math.round(Math.atan2(dy,dx)*180/Math.PI*10)/10);
    }
    stage.addEventListener('pointerdown',e=>{if(action==='shoot'){stage.setPointerCapture(e.pointerId);target(e);}});
    stage.addEventListener('pointermove',e=>{if($('#shoot-follow').checked&&(e.pointerType==='mouse'||e.buttons))target(e);});
    $('#motion-image').addEventListener('load',()=>requestAnimationFrame(drawRay));window.addEventListener('resize',drawRay);sync();
  }
  function generated(){
    if(!enabled)return;invalidate();renderedAngle=snapshot.aim_angle||0;
    if(renderedAngle!==angle())setAngle(angle());else sync();
  }
  function onAction(name){if(!enabled)return;$('#shoot-controls').hidden=name!=='shoot';$('.motion-preview').classList.toggle('aiming',name==='shoot');sync();}
  return {init,invalidate,ready,angle,setAngle,generated,onAction,sync};
})();
