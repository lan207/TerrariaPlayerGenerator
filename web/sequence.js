'use strict';
window.SequenceEditor = (() => {
  let entries=[], selected=-1, previews=[], serial=0, readySerial=-1, pending=false;
  let enabled=false, debounce=null, abort=null, dragged=null;
  const clone=value=>structuredClone(value);
  const limits=(value,min,max)=>Math.max(min,Math.min(max,Number.isFinite(Number(value))?Number(value):min));
  const durationValue=value=>Math.round(limits(value,20,2000)/10)*10;
  function status(message) {if(enabled)$('#sequence-status').textContent=message;}
  function label(entry) {
    return entry.kind==='fixed' ? `${catalog.actions[entry.action]||('旧采样：'+catalog.legacy_actions?.[entry.action])} · ${entry.action==='shoot'?`${entry.aim_angle}°`:entry.frame+1}` :
      `自定义 · 身体 ${entry.pose.body_frame}`;
  }
  function ready() {return enabled && entries.length>0 && !pending && readySerial===serial && !!animations?.custom;}
  function invalidate() {
    serial++;readySerial=-1;pending=false;clearTimeout(debounce);abort?.abort();
    if(animations)delete animations.custom;
    if(enabled)status(entries.length?'外观更新后，请重新生成人物动作':'从预设加入固定帧，或新增自定义姿势');
  }
  function store() {try{localStorage.setItem('player-studio-sequence-v1',JSON.stringify(entries));}catch(_) {}}
  function renderList() {
    const list=$('#sequence-list');list.replaceChildren();
    entries.forEach((entry,index)=>{
      const card=document.createElement('div');card.className='sequence-card';card.draggable=true;
      card.classList.toggle('selected',index===selected);card.dataset.index=index;
      const choose=document.createElement('button');choose.type='button';choose.className='sequence-choose';
      choose.setAttribute('aria-label',`编辑第 ${index+1} 帧`);
      if(previews[index]) {const image=new Image();image.src=previews[index];image.alt='';choose.append(image);}
      const title=document.createElement('span');title.textContent=`${index+1}. ${label(entry)}`;
      const time=document.createElement('small');time.textContent=`${entry.duration} ms`;
      choose.append(title,time);choose.onclick=()=>select(index);card.append(choose);
      const controls=document.createElement('div');controls.className='sequence-card-tools';
      for(const [text,name,fn,disabled] of [
        ['←','向前移动',()=>move(index,index-1),index===0],
        ['→','向后移动',()=>move(index,index+1),index===entries.length-1],
        ['＋','复制',()=>insert(clone(entry),index+1),false],
        ['×','删除',()=>remove(index),false]]) {
        const button=document.createElement('button');button.type='button';button.textContent=text;
        button.title=name;button.setAttribute('aria-label',`${name}第 ${index+1} 帧`);
        button.disabled=disabled;button.onclick=fn;controls.append(button);
      }
      card.append(controls);
      card.ondragstart=e=>{dragged=index;e.dataTransfer.setData('text/plain',String(index));e.dataTransfer.effectAllowed='move';};
      card.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect='move';};
      card.ondrop=e=>{e.preventDefault();if(dragged!==null)move(dragged,index);dragged=null;};
      card.ondragend=()=>{dragged=null;};list.append(card);
    });
    $('#sequence-count').textContent=`${entries.length} / ${catalog.sequence.max_frames} 帧`;
    $('#sequence-empty').hidden=entries.length>0;
  }
  function fillForm() {
    const entry=entries[selected];$('#sequence-frame-editor').hidden=!entry;
    if(!entry)return;
    $('#sequence-selected').textContent=`编辑第 ${selected+1} 帧 · ${entry.kind==='fixed'?'固定姿势':'自定义姿势'}`;
    $('#sequence-duration').value=entry.duration;
    $('#sequence-fixed').hidden=entry.kind!=='fixed';$('#sequence-pose').hidden=entry.kind!=='custom';
    if(entry.kind==='fixed') {
      const actionSelect=$('#sequence-action');actionSelect.replaceChildren();
      for(const [key,name] of Object.entries(catalog.actions))actionSelect.append(new Option(name,key));
      if(!catalog.actions[entry.action])actionSelect.append(new Option(`旧采样：${catalog.legacy_actions?.[entry.action]||entry.action}`,entry.action));
      $('#sequence-action').value=entry.action;$('#sequence-action-frame').max=catalog.sequence.frame_counts[entry.action];
      $('#sequence-action-frame').value=entry.frame+1;
      $('#sequence-action-frame').disabled=entry.action==='shoot';
      $('#sequence-aim-label').hidden=entry.action!=='shoot';$('#sequence-aim-angle').value=entry.aim_angle||0;return;
    }
    const pose=entry.pose;
    for(const part of ['head','body','legs','whole']) {
      pose[part+'_transform'] ??= {angle:0,x:0,y:0};
      for(const key of ['angle','x','y'])$(`#pose-${part}-${key}`).value=pose[part+'_transform'][key];
    }
    for(const [id,key] of [['body','body_frame'],['head','head_frame'],['legs','leg_frame'],['effect','effect_frame'],['direction','direction']]) $(`#pose-${id}`).value=pose[key];
    for(const side of ['front','back']) {
      const arm=pose[side+'_arm'];$(`#pose-${side}-enabled`).checked=arm.enabled;
      $(`#pose-${side}-stretch`).value=arm.stretch;
      $(`#pose-${side}-angle`).value=arm.angle;$(`#pose-${side}-range`).value=arm.angle;
      for(const field of ['stretch','angle','range'])$(`#pose-${side}-${field}`).disabled=!arm.enabled;
    }
  }
  function select(index,focusPreview=true) {
    if(index<0||index>=entries.length)return;
    selected=index;renderList();fillForm();
    if(focusPreview&&ready()){selectAction('custom');selectFrame(selected);}
  }
  function changed(focus=true) {
    stop();serial++;readySerial=-1;abort?.abort();clearTimeout(debounce);pending=entries.length>0;
    if(animations)delete animations.custom;previews=[];store();renderList();fillForm();
    if(!entries.length){status('时间轴为空');if(action==='custom')selectAction('idle');return;}
    status('正在更新自定义帧…');
    if(snapshot)debounce=setTimeout(()=>render(focus),140);
    else {pending=false;status('请先确认人物并生成动作');}
  }
  async function render(focus=false) {
    if(!enabled||!entries.length||!snapshot)return;
    const version=serial, appearance=revision, chosen=clone(entries);abort=new AbortController();pending=true;
    status('正在生成时间轴预览…');
    try {
      const data=await(await api('/api/sequence',{config:clone(snapshot),sequence:chosen},abort.signal)).json();
      if(version!==serial||appearance!==revision||!animations)return;
      previews=data.images;animations.custom=data.images;readySerial=version;pending=false;
      renderList();fillForm();status(`已就绪 · ${entries.length} 帧 · ${entries.reduce((sum,e)=>sum+e.duration,0)} ms`);
      if(focus||action==='custom'){selectAction('custom');selectFrame(Math.max(selected,0));}
    } catch(error) {
      if(error.name==='AbortError'||version!==serial)return;
      pending=false;status('生成失败，可点击“重新预览”重试');toast(error.message,true);
    }
  }
  function insert(entry,index=entries.length) {
    if(entries.length>=catalog.sequence.max_frames){toast('时间轴最多 120 帧',true);return;}
    entries.splice(index,0,entry);selected=index;changed();
  }
  function remove(index) {entries.splice(index,1);selected=Math.min(index,entries.length-1);changed();}
  function move(from,to) {
    if(from===to||from<0||to<0||from>=entries.length||to>=entries.length)return;
    const chosen=entries[selected], [entry]=entries.splice(from,1);entries.splice(to,0,entry);
    selected=entries.indexOf(chosen);changed();
  }
  function currentEntry() {
    if(action==='custom'&&entries[frame])return clone(entries[frame]);
    const fixed=catalog.actions[action]?action:'idle';
    return {kind:'fixed',action:fixed,frame:Math.min(frame,catalog.sequence.frame_counts[fixed]-1),duration:interval(),
      ...(fixed==='shoot'?{aim_angle:window.AimControl.angle()}: {})};
  }
  function updatePose() {
    const entry=entries[selected];if(entry?.kind!=='custom')return;
    for(const [id,key] of [['body','body_frame'],['head','head_frame'],['legs','leg_frame'],['effect','effect_frame'],['direction','direction']])entry.pose[key]=Number($(`#pose-${id}`).value);
    entry.pose.effect_frame=Math.round(limits(entry.pose.effect_frame,0,7));
    for(const part of ['head','body','legs','whole'])entry.pose[part+'_transform']=Object.fromEntries(
      ['angle','x','y'].map(key=>[key,limits($(`#pose-${part}-${key}`).value,key==='angle'?-180:-128,key==='angle'?180:128)]));
    for(const side of ['front','back'])entry.pose[side+'_arm']={enabled:$(`#pose-${side}-enabled`).checked,
      stretch:$(`#pose-${side}-stretch`).value,angle:limits($(`#pose-${side}-angle`).value,-180,180)};
    changed();
  }
  function init() {
    if(!catalog.sequence)return;enabled=true;
    const root=$('#sequence-editor');root.hidden=false;
    root.innerHTML=`<div class="sequence-heading"><div><h3>自定义时间轴 <span id="sequence-count"></span></h3><p class="hint">把固定姿势与自定义双臂混合编排。拖动卡片或使用箭头调换顺序。</p></div><button id="sequence-preview" type="button">重新预览</button></div>
      <div class="sequence-toolbar"><button id="sequence-add-current" type="button">＋ 加入当前动作帧</button><button id="sequence-add-action" type="button">＋ 加入整个动作</button><button id="sequence-add-custom" class="accent" type="button">＋ 自定义姿势帧</button><button id="sequence-clear" class="quiet" type="button">清空时间轴</button></div>
      <p id="sequence-empty" class="hint">先在上方选择动作和帧，然后添加到这里。</p><div id="sequence-list" aria-label="自定义帧顺序"></div>
      <div id="sequence-frame-editor" hidden><div class="sequence-edit-heading"><strong id="sequence-selected"></strong><label>帧时长 <input id="sequence-duration" type="number" min="20" max="2000" step="10" value="100"> ms</label></div>
      <div id="sequence-fixed" class="pose-fields"><label>固定动作<select id="sequence-action"></select></label><label>动作第几帧<input id="sequence-action-frame" type="number" min="1" value="1"></label><label id="sequence-aim-label" hidden>瞄准角度（°）<input id="sequence-aim-angle" type="number" min="-180" max="180" step="0.1" value="0"></label></div>
      <div id="sequence-pose"><div class="pose-fields"><label>身体状态<select id="pose-body"></select></label><label>头部帧<select id="pose-head"></select></label><label>腿部状态<select id="pose-legs"></select></label><label>朝向<select id="pose-direction"><option value="1">朝右</option><option value="-1">朝左</option></select></label><label>饰品 / 特效帧<input id="pose-effect" type="number" min="0" max="7" value="0"></label></div><div id="pose-arms" class="pose-arms"></div>
      <p class="hint">角度以朝右时为基准：0° 向下，−90° 向前，±180° 向上；朝左时镜像。关闭自定义手臂即可跟随身体原版姿势。气球循环 4 帧，Extra_73 循环 8 帧。</p></div></div>
      <p id="sequence-status" class="hint" role="status"></p><p class="hint">选择上方“自定义”动作后，底部按钮会导出整条时间轴；GIF 使用各帧的时长。时间轴编排自动保存在此浏览器。</p>`;
    const tab=document.createElement('button');tab.type='button';tab.textContent='自定义';tab.dataset.action='custom';tab.setAttribute('role','tab');
    const transforms=document.createElement('div');transforms.className='pose-arms pose-transforms';
    for(const [part,name] of [['head','头部'],['body','身体（含双臂）'],['legs','腿部'],['whole','全身']]) {
      const field=document.createElement('fieldset');field.innerHTML=`<legend>${name}变换</legend>`+
        [['angle','旋转（°）',180],['x','X 偏移（像素）',128],['y','Y 偏移（像素）',128]].map(([key,label,max])=>
        `<label>${label}<input id="pose-${part}-${key}" type="number" min="-${max}" max="${max}" step="0.1" value="0"></label>`).join('')+
        `<button id="pose-${part}-reset" type="button">重置${name}</button>`;
      transforms.append(field);
    }
    $('#sequence-pose').append(transforms);
    const hint=document.createElement('p');hint.className='hint';hint.textContent='部位旋转以颈部、躯干中心和髋部为支点，正角度顺时针。部位偏移随朝向镜像；全身变换最后应用，X 向右、Y 向下。装备与饰品跟随所属部位；画布自动扩展。';
    $('#sequence-pose').append(hint);
    for(const part of ['head','body','legs','whole']) {
      for(const key of ['angle','x','y'])$(`#pose-${part}-${key}`).onchange=updatePose;
      $(`#pose-${part}-reset`).onclick=()=>{for(const key of ['angle','x','y'])$(`#pose-${part}-${key}`).value=0;updatePose();};
    }
    tab.onclick=()=>{if(ready())selectAction('custom');else if(entries.length)render(true);else toast('请先向时间轴添加帧');};$('#action-tabs').append(tab);
    for(const [key,name] of Object.entries(catalog.actions))$('#sequence-action').append(new Option(name,key));
    for(let i=0;i<20;i++) {
      const label=i===0?'站立':i===5?'跳跃':i>=7?`跑动 ${i-6}`:`姿势 ${i}`;
      for(const key of ['body','head','legs'])$(`#pose-${key}`).append(new Option(`${i} · ${label}`,String(i)));
    }
    for(const [side,name] of [['front','前手'],['back','后手']]) {
      const field=document.createElement('fieldset');field.innerHTML=`<legend>${name}</legend><label class="check"><input id="pose-${side}-enabled" type="checkbox" checked> 自定义${name}</label><label>伸展长度<select id="pose-${side}-stretch"></select></label><label>角度 <input id="pose-${side}-angle" type="number" min="-180" max="180" step="1" value="0"> °</label><input id="pose-${side}-range" type="range" min="-180" max="180" value="0" aria-label="${name}角度">`;
      $('#pose-arms').append(field);
      for(const [key,label] of Object.entries(catalog.sequence.stretches))$(`#pose-${side}-stretch`).append(new Option(label,key));
      for(const key of ['enabled','stretch','angle'])$(`#pose-${side}-${key}`).onchange=updatePose;
      $(`#pose-${side}-range`).oninput=e=>{$(`#pose-${side}-angle`).value=e.target.value;updatePose();};
    }
    for(const key of ['body','head','legs','direction','effect'])$(`#pose-${key}`).onchange=updatePose;
    $('#sequence-duration').onchange=e=>{if(entries[selected]){entries[selected].duration=durationValue(e.target.value);changed();}};
    $('#sequence-action').onchange=e=>{if(entries[selected]?.kind==='fixed'){
      const entry=entries[selected];entry.action=e.target.value;entry.frame=0;
      if(entry.action==='shoot')entry.aim_angle=window.AimControl.angle();else delete entry.aim_angle;changed();}};
    $('#sequence-aim-angle').onchange=e=>{const entry=entries[selected];if(entry?.kind==='fixed'&&entry.action==='shoot'){
      entry.aim_angle=limits(e.target.value,-180,180);changed();}};
    $('#sequence-action-frame').onchange=e=>{const entry=entries[selected];if(entry?.kind==='fixed'){
      entry.frame=Math.round(limits(e.target.value,1,catalog.sequence.frame_counts[entry.action]))-1;changed();}};
    $('#sequence-add-current').onclick=()=>{if(action==='shoot'&&!window.AimControl.ready()){toast('请等当前瞄准更新完成');return;}insert(currentEntry());};
    $('#sequence-add-custom').onclick=()=>{const pose=clone(catalog.sequence.default_pose);pose.direction=config.direction;insert({kind:'custom',pose,duration:interval()});};
    $('#sequence-add-action').onclick=()=>{
      if(action==='custom'){toast('请先选择一个预设动作');return;}
      if(action==='shoot'){if(!window.AimControl.ready()){toast('请等当前瞄准更新完成');return;}insert(currentEntry());return;}
      const count=catalog.sequence.frame_counts[action];if(entries.length+count>catalog.sequence.max_frames){toast('加入后会超过 120 帧',true);return;}
      const start=entries.length;for(let i=0;i<count;i++)entries.push({kind:'fixed',action,frame:i,duration:interval()});selected=start;changed();
    };
    $('#sequence-clear').onclick=()=>{entries=[];selected=-1;changed();};
    $('#sequence-preview').onclick=()=>render(true);
    try {
      const saved=JSON.parse(localStorage.getItem('player-studio-sequence-v1'));
      // Preserve old timelines: their three "shoot frames" were angle choices.
      if(Array.isArray(saved))for(const entry of saved)if(entry?.kind==='fixed'&&entry.action==='shoot'&&entry.aim_angle===undefined&&[0,1,2].includes(entry.frame)){
        entry.aim_angle=[-60,0,60][entry.frame];entry.frame=0;
      }
      if(Array.isArray(saved)&&saved.length<=catalog.sequence.max_frames&&saved.every(e=>e&&Number.isInteger(e.duration)&&e.duration>=20&&e.duration<=2000&&
        (e.kind==='fixed'&&(catalog.actions[e.action]||catalog.legacy_actions?.[e.action])&&Number.isInteger(e.frame)&&e.frame>=0&&e.frame<catalog.sequence.frame_counts[e.action]&&
         (e.action!=='shoot'||typeof e.aim_angle==='number'&&Number.isFinite(e.aim_angle)&&Math.abs(e.aim_angle)<=180)||
         e.kind==='custom'&&e.pose&&e.pose.front_arm&&e.pose.back_arm))) entries=saved;
    }catch(_) {}
    selected=entries.length?0:-1;renderList();fillForm();status('选择动作和帧，开始编排');
  }
  return {init,invalidate,regenerate:()=>render(false),ready,frames:()=>clone(entries),duration:index=>entries[index]?.duration||100};
})();
