import base64
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import sys
from threading import Thread
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.test-tools')]
from PIL import Image
from playwright.sync_api import sync_playwright
from web_server import Handler

class QuietHandler(Handler):
    def log_message(self,*_):pass

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    Thread(target=server.serve_forever,daemon=True).start()
    out=ROOT/'test-artifacts/aiming';out.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            # Old sampled item poses and old 3-index shooting frames migrate without being dropped.
            page.evaluate("localStorage.setItem('player-studio-sequence-v1',JSON.stringify([{kind:'fixed',action:'shoot',frame:2,duration:100},{kind:'fixed',action:'guitar',frame:1,duration:100}]))")
            page.reload();page.wait_for_function("!document.querySelector('#generate').disabled")
            saved=page.evaluate('SequenceEditor.frames()');assert saved[0]['frame']==0 and saved[0]['aim_angle']==60 and saved[1]['action']=='guitar'
            page.locator('#generate').click();page.wait_for_function('SequenceEditor.ready()')
            assert page.locator('[data-action]').count()==7
            assert page.locator('[data-action=guitar]').count()==0
            page.locator('#sequence-clear').click()
            page.locator('[data-action=shoot]').click();page.wait_for_function('AimControl.ready()')
            assert page.locator('.frame-thumb').count()==1 and page.locator('#play').is_disabled()
            page.locator('#shoot-angle').fill('-70.5');page.locator('#shoot-angle').press('Tab');page.wait_for_function('AimControl.ready()')
            assert page.evaluate('AimControl.angle()')==-70.5
            upper=page.locator('#motion-image').get_attribute('src')
            page.locator('#sequence-add-current').click();page.wait_for_function('SequenceEditor.ready()')
            assert page.evaluate('SequenceEditor.frames()[0].aim_angle')==-70.5
            page.locator('[data-action=shoot]').click()
            page.locator('#shoot-angle').fill('120.25');page.locator('#shoot-angle').press('Tab');page.wait_for_function('AimControl.ready()')
            assert '朝左' in page.locator('#shoot-state').inner_text()
            assert upper!=page.locator('#motion-image').get_attribute('src')
            page.locator('#sequence-add-action').click();page.wait_for_function('SequenceEditor.ready()')
            assert len(page.evaluate('SequenceEditor.frames()'))==2
            assert page.evaluate('SequenceEditor.frames()[1].aim_angle')==120.25
            # Every saved shot has an editable target, independently of the live target.
            page.locator('#sequence-aim-angle').fill('15.5');page.locator('#sequence-aim-angle').press('Tab');page.wait_for_function('SequenceEditor.ready()')
            assert page.evaluate('SequenceEditor.frames()[1].aim_angle')==15.5
            page.locator('[data-action=shoot]').click()
            stage=page.locator('.motion-preview');stage.scroll_into_view_if_needed();box=stage.bounding_box()
            page.mouse.move(box['x']+5,box['y']+20);page.wait_for_function('AimControl.ready()')
            assert page.evaluate('AimControl.angle()') < -90
            assert '朝左' in page.locator('#shoot-state').inner_text()
            assert page.locator('.frame-thumb').count()==1
            # Leaving the preview freezes the target; export is one frame and omits the guide ray.
            page.mouse.move(1200,100)
            url=page.locator('#motion-image').get_attribute('src')
            expected=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
            for kind in ('frame','sheet','gif'):
                with page.expect_download() as event:page.locator(f'[data-export={kind}]').click()
                dest=out/event.value.suggested_filename;event.value.save_as(dest)
                with Image.open(dest) as image:
                    assert image.size==expected.size
                    if kind=='gif':assert image.n_frames==1
                    else:assert image.convert('RGBA').tobytes()==expected.tobytes()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out/'phone.png'),full_page=True)
            assert not errors,errors
            browser.close();print('PASS: six main actions, legacy timeline migration, single-frame arbitrary-angle aiming, mouse-facing, per-frame angle capture/edit, frozen PNG/sheet/GIF exports, mobile layout.')
    finally:server.shutdown()

if __name__=='__main__':main()
