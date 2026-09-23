"""Compare the independent mobile renderer against Pillow and exercise mobile UI/export."""
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import random
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.test-tools'))
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
from mobile.prepare import prepare
from TrueTerrariaGenerator import TerrariaCharacterGenerator, USE_FRAMES
from web_server import DEFAULTS, configuration
from poses import DEFAULT_POSE


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass


def main():
    assets = prepare()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(assets)))
    Thread(target=server.serve_forever, daemon=True).start()
    out = ROOT / 'test-artifacts/mobile'
    out.mkdir(parents=True, exist_ok=True)
    generator = TerrariaCharacterGenerator()
    random.seed(17)
    cases = []
    # Every hair and Alt texture, mixed outfits, directions, and walk frames.
    for alt in (False, True):
        for hair in range(1,166):
            c = DEFAULTS | dict(hair=hair,alt_hair=alt,skin_variant=hair%10,
                pants_variant=(hair+3)%10,shoes_variant=(hair+7)%10,direction=-1 if hair%2 else 1)
            cases.append((c, 'walk', hair%13))
    for variant in range(10):
        for action in ('idle','walk','jump','use'):
            for style in (USE_FRAMES if action == 'use' else [1]):
                c = DEFAULTS | dict(skin_variant=variant,use_style=style,hair=164 if variant%2 else 165)
                for key in c:
                    if key.endswith('_color'): c[key] = f'#{random.randrange(0x1000000):06x}'
                for frame in range(len(generator.action_frames(action,style))): cases.append((c,action,frame))
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
            errors=[]
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_function("document.querySelector('#preview-state').textContent === '预览已更新'",timeout=120000)
            differences=[]
            for n,(c,action,frame) in enumerate(cases):
                url=page.evaluate('async ([c,a,f]) => (await LocalPlayer.compose(c,a,f)).toDataURL()', [c,action,frame])
                actual=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
                expected=generator.compose(**configuration(c)[1],action=action,action_frame=frame)
                delta=ImageChops.difference(actual,expected)
                maximum=max(hi for lo,hi in delta.getextrema())
                if maximum:
                    differences.append(dict(case=n,hair=c['hair'],alt=c['alt_hair'],variant=c['skin_variant'],action=action,frame=frame,max_delta=maximum))
                if maximum > 2:
                    actual.save(out/'mismatch-actual.png'); expected.save(out/'mismatch-expected.png')
                    raise AssertionError(differences[-1])
                if n%100==0: print(f'Compared {n+1}/{len(cases)} frames',flush=True)
            # Verify the new Android layer compositor against Pillow for both
            # equipment and extended whole-body transform bounds.
            parity_cases=[(DEFAULTS|{'armor_head':1,'armor_body':1,'armor_legs':1},None),
                          (DEFAULTS,DEFAULT_POSE|{'whole_transform':{'angle':45,'x':48,'y':-2}})]
            for character,pose in parity_cases:
                url=page.evaluate('async ([c,p])=>(await LocalPlayer.compose(c,"idle",0,p)).toDataURL()', [character,pose])
                actual=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
                expected=generator.compose(**configuration(character)[1],**({'pose':pose} if pose else {}))
                assert actual.size==expected.size,(actual.size,expected.size)
                assert ImageChops.difference(actual,expected).getbbox() is None,'Equipment/transform render differs from Pillow'
            page.locator('#generate').click()
            page.locator('#animation-content').wait_for(state='visible')
            page.locator('[data-action=walk]').click()
            assert page.locator('.frame-thumb').count()==13
            page.locator('#export-scale').select_option('8')
            for kind in ('frame','sheet','gif'):
                with page.expect_download() as event: page.locator(f'[data-export={kind}]').click()
                destination=out/event.value.suggested_filename
                event.value.save_as(destination)
                im=Image.open(destination)
                assert im.size == (4160 if kind=='sheet' else 320,448), im.size
                if kind=='gif':
                    assert im.n_frames==13 and im.info['loop']==0 and im.info['duration']==100
                    for i in range(13):
                        im.seek(i)
                        expected=generator.compose(**configuration(DEFAULTS)[1],action='walk',action_frame=i).resize((320,448),Image.Resampling.NEAREST)
                        actual=im.convert('RGBA')
                        # Transparent RGB values are irrelevant; compare visible pixels and alpha separately.
                        assert ImageChops.difference(actual.getchannel('A'),expected.getchannel('A')).getbbox() is None
                        assert ImageChops.difference(actual.convert('RGB'),expected.convert('RGB')).getbbox() is None
            # Ensure changing the character invalidates existing animation exports.
            page.locator('#base-tab').click()
            page.locator('[aria-label="下一个发型"]').click()
            assert not page.locator('#animation-content').is_visible()
            page.wait_for_function("document.querySelector('#preview-state').textContent === '预览已更新'")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out/'mobile.png'),full_page=True)
            assert not errors, errors
            browser.close()
            (out/'verification.json').write_text(json.dumps({'frames':len(cases),'rounding_differences':differences,'ui_errors':errors},indent=2),encoding='utf-8')
            print(f'PASS: {len(cases)} frames; PNG/sheet/GIF 8x; mobile UI. Rounding differences: {len(differences)}')
    finally: server.shutdown()


if __name__ == '__main__': main()
