'use strict';
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let catalog, config, snapshot, animations, action = 'idle', frame = 0;
let timer = null, previewTimer = null, previewAbort = null, revision = 0, generating = false;
let toastTimer;
const parts = [
  ['hair', '发型', 'HAIR'], ['skin_variant', '身体 / 上衣', 'BODY'],
  ['pants_variant', '裤装', 'PANTS'], ['shoes_variant', '鞋子', 'SHOES']
];
const colors = [
  ['hair_color', '头发', 'hair'], ['skin_color', '皮肤', 'skin'],
  ['eye_color', '眼睛', 'eyes'], ['shirt_color', '上衣', 'shirt'],
  ['undershirt_color', '内衫 / 衣袖', 'undershirt'],
  ['pants_color', '裤装', 'pants'], ['shoes_color', '鞋子', 'shoes']
];
const equipmentSlots = [['head','头部'],['body','上身'],['legs','腿部']];
let visibleAccessoryTextures = {}, visibleAccessoryDyeSources = {};

function dyeColor(group, slot) {
  const own=config[group]?.[slot];
  if(own)return own;
  if(group==='accessory_dyes' && !config.accessories[slot]) {
    const source=visibleAccessoryDyeSources[slot];
    if(source==='body'&&config.auto_capes)return config.armor_dyes?.body || '#ffffff';
    if(source&&source!==slot&&config.accessories[source])return config.accessory_dyes[source]||'#ffffff';
  }
  return '#ffffff';
}

function dyeControl(group, slotGetter, id, label) {
  const row=document.createElement('div');row.className='dye-control';row.dataset.dyeGroup=group;row.dataset.dyeId=id;
  row.innerHTML=`<label for="pick-dye-${id}">${label}</label><div class="dye-inputs"><input id="pick-dye-${id}" type="color" value="#ffffff" aria-label="${label}取色"><input id="hex-dye-${id}" class="hex" value="#FFFFFF" maxlength="7" spellcheck="false" aria-label="${label}颜色代码"><button id="reset-dye-${id}" type="button" title="恢复原色或配套部件的颜色">重置</button></div>`;
  row.dyeSlot=slotGetter;
  row.querySelector('input[type=color]').oninput=e=>{config[group][slotGetter()]=e.target.value.toLowerCase();changed();};
  row.querySelector('.hex').onchange=e=>{
    let value=e.target.value.trim();if(!value.startsWith('#'))value='#'+value;
    if(!/^#[0-9a-f]{6}$/i.test(value)){toast('请输入六位颜色，例如 #508CBE',true);refreshDyes();return;}
    config[group][slotGetter()]=value.toLowerCase();changed();
  };
  row.querySelector('button').onclick=()=>{delete config[group][slotGetter()];changed();};
  return row;
}

function refreshDyes() {
  if(!catalog.dyes)return;
  for(const row of $$('.dye-control')) {
    const color=dyeColor(row.dataset.dyeGroup,row.dyeSlot());
    row.querySelector('input[type=color]').value=color;row.querySelector('.hex').value=color.toUpperCase();
  }
}

function equipmentOptions(slot) {
  const select = $(`#armor-${slot}`), query = $(`#search-${slot}`).value.trim().toLowerCase();
  const value = config[`armor_${slot}`];
  select.replaceChildren(new Option('不穿戴', '0'));
  for (const item of catalog.equipment[slot]) {
    if (item.id !== value && query && !`${item.id} ${item.name} ${item.key} ${item.texture}`.toLowerCase().includes(query)) continue;
    const option = new Option(`${item.name} · #${item.id}${item.available ? '' : '（素材不完整）'}`, String(item.id));
    option.disabled = !item.available; option.title = item.note;
    select.append(option);
  }
  select.value = value;
}

function buildEquipment() {
  if (!catalog.equipment) return;
  $('#appearance-tabs').hidden = false;
  const selectPane = pane => {
    $('#base-options').hidden = pane !== 'base';
    $('#equipment-panel').hidden = pane !== 'gear';
    $('#accessory-panel').hidden = pane !== 'accessory';
    for (const [id,selected] of [['base-tab',pane==='base'],['gear-tab',pane==='gear'],['accessory-tab',pane==='accessory']]) {
      $(`#${id}`).classList.toggle('active',selected);
      $(`#${id}`).setAttribute('aria-selected',String(selected));
    }
  };
  $('#base-tab').onclick = () => selectPane('base');
  $('#gear-tab').onclick = () => selectPane('gear');
  $('#accessory-tab').onclick = () => selectPane('accessory');
  if (catalog.accessories) {$('#accessory-tab').hidden=false;buildAccessories();}
  selectPane('gear');
  for (const [slot,label] of equipmentSlots) {
    const row = document.createElement('div'); row.className = 'equipment-slot';
    row.innerHTML = `<label for="armor-${slot}">${label}</label><input type="search" id="search-${slot}" placeholder="搜索名称 / 编号" aria-label="搜索${label}装备"><div class="equipment-choice"><button type="button" aria-label="上一件${label}装备">‹</button><select id="armor-${slot}" aria-label="${label}装备"></select><button type="button" aria-label="下一件${label}装备">›</button></div><code id="equipped-${slot}" class="texture-name"></code>`;
    $('#equipment-slots').append(row);
    $(`#search-${slot}`).oninput = () => equipmentOptions(slot);
    $(`#armor-${slot}`).onchange = e => {config[`armor_${slot}`]=Number(e.target.value);changed();};
    row.querySelectorAll('button').forEach((button,index) => {
      button.onclick = () => {
        const select = $(`#armor-${slot}`), values = [...select.options].filter(o=>!o.disabled).map(o=>Number(o.value));
        config[`armor_${slot}`]=values[(values.indexOf(config[`armor_${slot}`])+(index ? 1 : -1)+values.length)%values.length];
        changed();
      };
    });
    if(catalog.dyes)row.append(dyeControl('armor_dyes',()=>slot,`armor-${slot}`,`${label}染色`));
  }
  $('#clear-equipment').onclick = () => {
    for (const [slot] of equipmentSlots) {config[`armor_${slot}`]=0;$(`#search-${slot}`).value='';}
    changed();
  };
}

function accessoryOptions() {
  if (!catalog.accessories) return;
  const slot=$('#accessory-slot').value, query=$('#accessory-search').value.trim().toLowerCase();
  const select=$('#accessory-item'), chosen=config.accessories[slot]||0;
  const automatic=!chosen&&catalog.accessories[slot].items.find(item=>item.texture===visibleAccessoryTextures[slot]);
  select.replaceChildren(new Option(automatic?`自动配套：${automatic.name}`:'不佩戴','0'));
  for (const item of catalog.accessories[slot].items) {
    if (item.id!==chosen && query && !`${item.id} ${item.name} ${item.key}`.toLowerCase().includes(query)) continue;
    select.append(new Option(`${item.name} · #${item.id}`,String(item.id)));
  }
  select.value=chosen; $('#auto-capes').checked=config.auto_capes;
  const list=$('#accessory-equipped');list.replaceChildren();
  for (const [key,value] of Object.entries(config.accessories)) {
    if (!value) continue;
    const item=catalog.accessories[key].items.find(e=>e.id===value), button=document.createElement('button');
    button.type='button';button.textContent=`${catalog.accessories[key].label}：${item?.name||value} ×`;
    if(catalog.dyes)button.style.borderLeft=`3px solid ${dyeColor('accessory_dyes',key)}`;
    button.onclick=()=>{delete config.accessories[key];changed();};list.append(button);
  }
  if (!list.children.length) list.textContent='尚未选择饰品';
  refreshDyes();
}

function buildAccessories() {
  for (const [key,entry] of Object.entries(catalog.accessories)) $('#accessory-slot').append(new Option(entry.label,key));
  $('#accessory-slot').onchange=()=>{$('#accessory-search').value='';accessoryOptions();};
  $('#accessory-search').oninput=accessoryOptions;
  $('#accessory-item').onchange=e=>{const key=$('#accessory-slot').value,value=Number(e.target.value);
    if(value)config.accessories[key]=value;else delete config.accessories[key];changed();};
  $('#auto-capes').onchange=e=>{config.auto_capes=e.target.checked;changed();};
  $('#accessory-clear').onclick=()=>{config.accessories={};config.auto_capes=false;changed();};
  if(catalog.dyes)$('#accessory-item').after(dyeControl('accessory_dyes',()=>$('#accessory-slot').value,'accessory','当前部位染色'));
}

function sizeImage(element, width, height, desktopScale, mobileScale) {
  element.style.setProperty('--source-width',`${width}px`);
  element.style.setProperty('--source-height',`${height}px`);
  element.style.setProperty('--zoom-desktop',desktopScale);
  element.style.setProperty('--zoom-mobile',mobileScale);
}

function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').className = error ? 'error' : '';
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 4800);
}

async function api(path, body, signal) {
  if (window.LocalPlayer) return window.LocalPlayer.request(path, body, signal);
  const response = await fetch(path, {method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body), signal});
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `请求失败 (${response.status})`);
  }
  return response;
}

function stop() {
  clearTimeout(timer); timer = null;
  $('#play').textContent = '▶ 播放';
}

function changed() {
  window.AimControl?.invalidate();
  window.SequenceEditor?.invalidate();
  if (window.LocalPlayer || catalog.sequence) {
    try {localStorage.setItem('player-studio-config', JSON.stringify(config));} catch (_) {}
  }
  revision++;
  stop(); animations = null; snapshot = null;
  $('#animation-content').hidden = true;
  $('#empty-state').hidden = false;
  $('#animation-state').textContent = '外观已更新 · 待生成';
  $('#preview-state').textContent = '正在更新…';
  $('#generate').disabled = true;
  refreshControls();
  clearTimeout(previewTimer);
  previewAbort?.abort();
  previewTimer = setTimeout(preview, 120);
}

function refreshControls() {
  accessoryOptions();
  refreshDyes();
  for (const [key] of parts) {
    const list = key === 'hair' ? catalog.hairs : catalog.variants.map((_, i) => i);
    $(`#value-${key}`).textContent = key === 'hair' ? `发型 ${config[key]}` : catalog.variants[config[key]];
    $(`#count-${key}`).textContent = `${String(list.indexOf(config[key])+1).padStart(2,'0')} / ${list.length}`;
  }
  for (const [key] of colors) {
    $(`#pick-${key}`).value = config[key];
    $(`#hex-${key}`).value = config[key].toUpperCase();
  }
  $('#alt-hair').checked = config.alt_hair;
  if (catalog.equipment) {
    for (const [slot] of equipmentSlots) equipmentOptions(slot);
    $('#alt-hair').disabled = config.armor_head !== 0;
    $('#alt-hair').parentElement.title = config.armor_head ? '穿戴头部装备时，按原版规则自动选择发型' : '';
  }
  $('#use-style').value = config.use_style;
  $$('[data-direction]').forEach(b => b.classList.toggle('active', Number(b.dataset.direction) === config.direction));
}

async function preview() {
  const version = revision;
  previewAbort = new AbortController();
  try {
    const data = await (await api('/api/preview', {config}, previewAbort.signal)).json();
    if (version !== revision) return;
    $('#base-image').src = data.image;
    document.body.classList.toggle('has-equipment', data.width > 40);
    if (data.width) $('.spec strong').textContent = `${data.width} × ${data.height}`;
    if (data.width) sizeImage($('#base-image'),data.width,data.height,data.height>80?3:data.width>40?4:5,data.width>40?3:4);
    if (catalog.accessories) {
      visibleAccessoryTextures=data.textures.accessories||{};
      visibleAccessoryDyeSources=data.textures.accessory_dye_sources||{};
      $('#accessory-textures').textContent=Object.values(data.textures.accessories||{}).join(' · ')||'无可见饰品';
      accessoryOptions();
    }
    if (catalog.equipment) {
      for (const [slot] of equipmentSlots) $(`#equipped-${slot}`).textContent = data.textures.equipment[slot].join(' · ') || '未穿戴';
      const body = config.armor_body && catalog.equipment.body.find(e=>e.id===config.armor_body);
      $('#equipment-note').textContent = body && data.textures.equipment.legs[0] !== catalog.equipment.legs.find(e=>e.id===config.armor_legs)?.texture ?
        '实际腿装已按原版体型或上身配套规则自动适配，配套衣摆跟随上身染色。' : '各部位可独立染色。白色保留原色；头发与衣摆自动适配。';
    }
    for (const [, , part] of colors) {
      const label = $(`#texture-${part}`);
      label.textContent = data.textures[part].join(' · ');
      label.title = data.textures[part].join('\n');
    }
    $('#preview-state').textContent = '预览已更新';
    $('#generate').disabled = generating;
  } catch (error) {
    if (error.name === 'AbortError' || version !== revision) return;
    $('#preview-state').textContent = '预览失败，请重试';
    toast(error.message, true);
  }
}

function stepPart(key, step) {
  const list = key === 'hair' ? catalog.hairs : catalog.variants.map((_, i) => i);
  config[key] = list[(list.indexOf(config[key]) + step + list.length) % list.length];
  changed();
}

function buildControls() {
  for (const [key, label, short] of parts) {
    const row = document.createElement('div'); row.className = 'part';
    row.innerHTML = `<div class="part-label">${label} <span id="count-${key}"></span></div>
      <div class="part-controls"><button type="button" aria-label="上一个${label}">‹</button>
      <strong id="value-${key}"></strong><button type="button" aria-label="下一个${label}">›</button></div>`;
    const buttons = row.querySelectorAll('button');
    buttons[0].onclick = () => stepPart(key, -1);
    buttons[1].onclick = () => stepPart(key, 1);
    let start = null;
    row.addEventListener('pointerdown', e => { start = [e.clientX, e.clientY]; });
    row.addEventListener('pointerup', e => {
      if (!start) return;
      const dx = e.clientX - start[0], dy = e.clientY - start[1]; start = null;
      if (Math.abs(dx) > 35 && Math.abs(dx) > Math.abs(dy)) stepPart(key, dx < 0 ? 1 : -1);
    });
    row.addEventListener('pointercancel', () => {start = null;});
    $('#selectors').append(row);
  }
  for (const [key, label, part] of colors) {
    const row = document.createElement('div'); row.className = 'color-row';
    row.innerHTML = `<div class="color-top"><label for="pick-${key}">${label}</label>
      <input type="color" id="pick-${key}" aria-label="${label}取色">
      <input class="hex" id="hex-${key}" aria-label="${label}颜色代码" maxlength="7" spellcheck="false"></div>
      <code class="texture-name" id="texture-${part}">正在读取贴图…</code>`;
    row.querySelector('input[type=color]').oninput = e => {config[key] = e.target.value; changed();};
    row.querySelector('.hex').onchange = e => {
      let value = e.target.value.trim(); if (!value.startsWith('#')) value = '#' + value;
      if (!/^#[0-9a-f]{6}$/i.test(value)) {toast('请输入六位颜色，例如 #508CBE', true); refreshControls(); return;}
      config[key] = value.toLowerCase(); changed();
    };
    $('#colors').append(row);
  }
  $('#alt-hair').onchange = e => {config.alt_hair = e.target.checked; changed();};
  $('#use-style').onchange = e => {config.use_style = Number(e.target.value); changed();};
  $$('[data-direction]').forEach(b => {b.onclick = () => {config.direction = Number(b.dataset.direction); changed();};});
  $('#reset').onclick = () => {config = structuredClone(catalog.defaults); changed();};
}

function selectFrame(index) {
  if (!animations?.[action]?.length) return;
  frame = (index + animations[action].length) % animations[action].length;
  $('#motion-image').src = animations[action][frame];
  $('#motion-image').onload=()=>{const im=$('#motion-image');sizeImage(im,im.naturalWidth,im.naturalHeight,im.naturalHeight>80?2:im.naturalWidth>40?3:4,im.naturalWidth>40?2:3);};
  $('#frame-label').textContent = `${String(frame + 1).padStart(2,'0')} / ${String(animations[action].length).padStart(2,'0')}`;
  $('#scrub').value = frame;
  $$('.frame-thumb').forEach((b, i) => {
    b.classList.toggle('active', i === frame); b.setAttribute('aria-pressed', String(i === frame));
  });
}

function selectAction(name) {
  if (!animations?.[name]?.length) return;
  stop(); action = name; frame = 0;
  $('#interval').disabled=action==='custom';
  $('#interval').title=action==='custom'?'自定义动画使用时间轴中设置的每帧时长':'';
  $$('[data-action]').forEach(b => {const selected = b.dataset.action === action;
    b.classList.toggle('active', selected); b.setAttribute('aria-selected', String(selected));});
  $('#frames').replaceChildren();
  animations[action].forEach((url, i) => {
    const b = document.createElement('button'); b.className = 'frame-thumb'; b.title = `第 ${i+1} 帧`;
    b.setAttribute('aria-label', b.title);
    const im = new Image(); im.src = url; im.alt = '';
    const count = document.createElement('span'); count.textContent = String(i+1).padStart(2,'0');
    b.append(im, count); b.onclick = () => {stop(); selectFrame(i);}; $('#frames').append(b);
  });
  $('#scrub').max = animations[action].length - 1;
  const single=animations[action].length===1;
  $('#play').disabled=single;$('#previous').disabled=single;$('#next').disabled=single;$('#scrub').disabled=single;
  if(action==='shoot'){$('#interval').disabled=true;$('#interval').title='射击是随瞄准方向更新的单帧';}
  $('#action-note').textContent = action==='custom' ? '按自定义时间轴的顺序与每帧时长播放、导出。' :
    action==='shoot' ? '当前瞄准只有一帧。普通射击按瞄准角选择身体贴图，不把上、平、下三个备选姿势串成动画。' :
    animations[action].length===1 ? '此动作使用单个固定姿势帧，可加入自定义时间轴。' : '点击帧缩略图可定位；可将此帧或整个动作加入自定义时间轴。动作不包含手持物品。';
  selectFrame(0);
  window.AimControl?.onAction(name);
}

function interval() {
  const value = Number($('#interval').value);
  return Number.isFinite(value) ? Math.max(20, Math.min(2000, Math.round(value / 10) * 10)) : 100;
}

function play() {
  if (!animations?.[action]?.length || animations[action].length===1) return;
  $('#play').textContent = 'Ⅱ 暂停';
  timer = setTimeout(() => {selectFrame(frame + 1); play();}, action==='custom' ? window.SequenceEditor.duration(frame) : interval());
}

async function generate() {
  if (generating) return;
  generating = true; const version = revision; const chosen = structuredClone(config);
  $('#generate').disabled = true; $('#generate').textContent = '正在生成动作…';
  try {
    const data = await (await api('/api/generate', {config: chosen})).json();
    if (version !== revision) {toast('生成期间外观已更改，请重新确认人物'); return;}
    snapshot = chosen; animations = data.animations;
    window.AimControl?.generated();
    $('#empty-state').hidden = true; $('#animation-content').hidden = false;
    $('#animation-state').textContent = `${Object.keys(data.animations).length} 组动作 · 已就绪`;
    selectAction('idle');
    window.SequenceEditor?.regenerate();
    $('.animation').scrollIntoView({behavior:'smooth', block:'start'});
  } catch (error) {toast(error.message, true);}
  finally {generating = false; $('#generate').textContent = '确认人物 · 生成动画 ↗';
    $('#generate').disabled = $('#preview-state').textContent !== '预览已更新';}
}

async function exportFile(kind, button) {
  if (!animations || !snapshot) return;
  if(action==='shoot'&&catalog.aiming&&!window.AimControl.ready()){toast('请等当前瞄准更新完成后再导出',true);return;}
  if (action==='custom' && !window.SequenceEditor.ready()) {toast('自定义时间轴正在更新或尚无帧，请稍后导出',true);return;}
  // Pause so the displayed frame and exported frame remain identical.
  stop(); const label = button.innerHTML; button.disabled = true; button.textContent = '导出中…';
  const chosenAction = action, chosenFrame = frame;
  try {
    const response = await api('/api/export', {config:snapshot, action:chosenAction, frame:chosenFrame,
      ...(chosenAction==='custom' ? {sequence:window.SequenceEditor.frames()} : {}),
      kind, interval:interval(), scale:Number($('#export-scale').value)});
    const blob = await response.blob();
    const filename = `player_${chosenAction}_${kind === 'frame' ? String(chosenFrame + 1).padStart(2,'0') : kind}.${kind === 'gif' ? 'gif' : 'png'}`;
    if (window.AndroidFiles) {
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('无法读取导出文件')); reader.readAsDataURL(blob);
      });
      window.AndroidFiles.save(filename, blob.type, data.split(',')[1]);
      return;
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url;
    link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000); toast('文件已生成，开始下载');
  } catch (error) {toast(error.message, true);}
  finally {button.disabled = false; button.innerHTML = label;}
}

async function init() {
  try {
    if (window.LocalPlayer) catalog = window.LocalPlayer.catalog;
    else {
      const response = await fetch('/api/catalog');
      if (!response.ok) throw new Error('无法读取素材目录');
      catalog = await response.json();
    }
    config = structuredClone(catalog.defaults);
    if (window.LocalPlayer || catalog.sequence) {
      try {
        const saved = JSON.parse(localStorage.getItem('player-studio-config'));
        if (saved) for (const key of Object.keys(config)) {
          const value = saved[key];
          if(key==='aim_angle'){if(typeof value==='number'&&Number.isFinite(value)&&value>=-180&&value<=180)config[key]=value;continue;}
          if(key==='armor_dyes'||key==='accessory_dyes') {
            const slots=key==='armor_dyes'?catalog.equipment:catalog.accessories;
            if(catalog.dyes&&slots&&value&&typeof value==='object'&&!Array.isArray(value))
              for(const [slot,color] of Object.entries(value))if(Object.hasOwn(slots,slot)&&typeof color==='string'&&/^#[0-9a-f]{6}$/i.test(color))config[key][slot]=color.toLowerCase();
            continue;
          }
          if (key==='accessories') {
            if(catalog.accessories && value && typeof value==='object' && !Array.isArray(value)) {
              config.accessories={};
              for(const [slot,id] of Object.entries(value))if(catalog.accessories[slot]?.items.some(e=>e.id===id))config.accessories[slot]=id;
            }
            continue;
          }
          if (key.endsWith('_color') ? /^#[0-9a-f]{6}$/i.test(value) :
              key === 'hair' ? catalog.hairs.includes(value) :
              key.endsWith('_variant') ? Number.isInteger(value) && value >= 0 && value < catalog.variants.length :
              key === 'direction' ? [-1,1].includes(value) :
              key.startsWith('armor_') ? value===0 || catalog.equipment?.[key.slice(6)]?.some(e=>e.id===value&&e.available) :
              key === 'use_style' ? catalog.use_styles.includes(value) : typeof value === 'boolean') config[key] = value;
        }
      } catch (_) { /* Ignore unavailable storage or old/corrupt settings. */ }
      document.addEventListener('visibilitychange', () => {
        try {localStorage.setItem('player-studio-config', JSON.stringify(config));} catch (_) {}
      });
    }
    buildControls(); buildEquipment(); refreshControls();
    for (const [name, label] of Object.entries(catalog.actions)) {
      const button = document.createElement('button'); button.textContent = label;
      button.dataset.action = name; button.setAttribute('role','tab');
      button.onclick = () => {if (animations) selectAction(name);}; $('#action-tabs').append(button);
    }
    window.AimControl?.init();window.SequenceEditor?.init();
    if (catalog.sequence) $('.use-style').hidden=true;
    $('#generate').onclick = generate;
    $('#play').onclick = () => {if (timer !== null) stop(); else play();};
    $('#previous').onclick = () => {stop(); selectFrame(frame - 1);};
    $('#next').onclick = () => {stop(); selectFrame(frame + 1);};
    $('#scrub').oninput = e => {stop(); selectFrame(Number(e.target.value));};
    $('#interval').onchange = () => {$('#interval').value = interval(); if (timer !== null) {stop(); play();}};
    $$('[data-export]').forEach(b => {b.onclick = () => exportFile(b.dataset.export, b);});
    document.addEventListener('visibilitychange', () => {if (document.hidden) stop();});
    await preview();
  } catch (error) {toast(error.message + (window.LocalPlayer ? '；请关闭应用后重试。' : '；请确认本地服务已启动并刷新页面。'), true);}
}
init();
