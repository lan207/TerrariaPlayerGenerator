"""Bundle the shared UI, offline renderer and textures (no server in the APK)."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web_server import DEFAULTS, VARIANTS, ACTIONS
from TrueTerrariaGenerator import USE_FRAMES, BACK_HAIR
from poses import DEFAULT_POSE, STRETCHES, FRAMES, LEGACY_ACTIONS, builtin_pose
from equipment import equipment_catalog, RULES, ROBES, COATS, LEG_MATCH, shoulder_offset
import accessories


def prepare():
    target = ROOT / 'mobile' / 'build' / 'assets'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'style.css', 'advanced.css', 'app.js', 'sequence.js', 'aim.js'):
        shutil.copyfile(ROOT / 'web' / name, target / name)
    html = (target / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<script src="/app.js"', '<script src="/catalog.js" defer></script><script src="/equipment.js" defer></script><script src="/render.js" defer></script><script src="/offline.js" defer></script><script src="/app.js"')
    (target / 'index.html').write_text(html, encoding='utf-8')
    shutil.copyfile(ROOT / 'mobile' / 'offline.js', target / 'offline.js')
    for name in ('equipment.js','render.js'):
        shutil.copyfile(ROOT/'mobile'/name,target/name)
    shutil.copytree(ROOT / 'Assets' / 'Player', target / 'Assets' / 'Player', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'Assets' / 'Hair', target / 'Assets' / 'Hair', dirs_exist_ok=True)
    for folder in ('Armor','Accessories'):
        shutil.copytree(ROOT/'Assets'/folder,target/'Assets'/folder,dirs_exist_ok=True)
    catalog = dict(defaults=DEFAULTS, variants=VARIANTS, actions=ACTIONS,
                   legacy_actions=LEGACY_ACTIONS, aiming=True, dyes=True,
                   equipment=equipment_catalog(), accessories=accessories.catalog(), rules=RULES,
                   frames=FRAMES, builtin_poses={a:[builtin_pose(a,i) for i in range(len(frames))] for a,frames in FRAMES.items()},
                   sequence=dict(default_pose=DEFAULT_POSE,stretches=STRETCHES,max_frames=120,frame_counts={a:len(f) for a,f in FRAMES.items()}),
                   equipment_maps=dict(ROBES=ROBES,COATS=COATS,LEG_MATCH=LEG_MATCH,OFFHAND=accessories.OFFHAND,
                        accessory_slots=accessories.SLOTS,CAPE_BACK_TO_FRONT=accessories.CAPE_BACK_TO_FRONT,
                        CAPE_FRONT_TO_BACK=accessories.CAPE_FRONT_TO_BACK,
                        shoulder_offsets={b:[shoulder_offset(b,f) for f in range(20)] for b in (55,71,183,204,201,101,207)}),
                   hairs=sorted(int(p.stem.rsplit('_', 1)[1]) for p in (ROOT / 'Assets/Hair').glob('Player_Hair_*.png')),
                   use_styles=list(USE_FRAMES), use_frames=USE_FRAMES, back_hair=sorted(BACK_HAIR),
                   player_files=sorted(p.name for p in (ROOT / 'Assets/Player').glob('*.png')))
    (target / 'catalog.js').write_text('window.OFFLINE_CATALOG = ' + json.dumps(catalog, ensure_ascii=False) + ';\n', encoding='utf-8')
    print(f'Offline assets: {target}')
    return target


if __name__ == '__main__':
    prepare()
