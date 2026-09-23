"""Exercise accessory controls, mixed custom timelines, ordering, timing and export."""
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
    output=ROOT/'test-artifacts/studio';output.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            page.locator('#accessory-tab').click()
            page.locator('#accessory-slot').select_option('back');page.locator('#accessory-item').select_option('1')
            page.locator('#accessory-slot').select_option('hand_on');page.locator('#accessory-item').select_option('1')
            page.locator('#accessory-slot').select_option('balloon');page.locator('#accessory-item').select_option('1')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#accessory-equipped button').count()==3
            page.locator('#gear-tab').click();page.locator('#armor-legs').select_option('140')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#equipped-legs').inner_text()=='Extra_73.png'
            assert page.locator('.spec strong').inner_text()=='64 × 96'
            page.locator('#generate').click();page.locator('#animation-content').wait_for(state='visible')
            assert page.locator('[data-action]').count()==7
            page.locator('[data-action=shoot]').click();page.locator('.frame-thumb').nth(0).click()
            page.locator('#sequence-add-current').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('#sequence-duration').fill('80');page.locator('#sequence-duration').press('Tab')
            page.wait_for_function('SequenceEditor.ready()')
            page.locator('#sequence-add-custom').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('#pose-front-angle').fill('-90');page.locator('#pose-front-angle').press('Tab')
            page.locator('#pose-back-angle').fill('45');page.locator('#pose-back-angle').press('Tab')
            page.locator('#pose-front-stretch').select_option('quarter')
            page.locator('#pose-body').select_option('5');page.locator('#pose-legs').select_option('1')
            page.locator('#pose-direction').select_option('-1');page.locator('#pose-effect').fill('3');page.locator('#pose-effect').press('Tab')
            page.locator('#sequence-duration').fill('180');page.locator('#sequence-duration').press('Tab')
            page.wait_for_function('SequenceEditor.ready()')
            descriptor=page.evaluate('SequenceEditor.frames()')
            assert descriptor[1]['pose']['front_arm']==dict(enabled=True,stretch='quarter',angle=-90)
            assert descriptor[1]['pose']['back_arm']['angle']==45
            assert descriptor[1]['duration']==180
            page.evaluate("""() => {
              for(const [part,angle,x,y] of [['head',20,-3,2],['body',-15,2,1],['legs',8,0,3],['whole',12,24,-2]])
                for(const [key,value] of Object.entries({angle,x,y}))document.querySelector(`#pose-${part}-${key}`).value=value;
              document.querySelector('#pose-head-angle').dispatchEvent(new Event('change',{bubbles:true}));
            }""")
            page.wait_for_function('SequenceEditor.ready()')
            transforms=page.evaluate('SequenceEditor.frames()[1].pose')
            assert transforms['head_transform']==dict(angle=20,x=-3,y=2)
            assert transforms['body_transform']==dict(angle=-15,x=2,y=1)
            assert transforms['legs_transform']==dict(angle=8,x=0,y=3)
            assert transforms['whole_transform']==dict(angle=12,x=24,y=-2)
            page.locator('#pose-head-reset').click();page.wait_for_function('SequenceEditor.ready()')
            transforms=page.evaluate('SequenceEditor.frames()[1].pose')
            assert transforms['head_transform']==dict(angle=0,x=0,y=0)
            assert transforms['whole_transform']==dict(angle=12,x=24,y=-2)
            # Duplicate and button-sort, then remove the duplicate.
            page.locator('[aria-label="复制第 2 帧"]').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('[aria-label="向前移动第 3 帧"]').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('[aria-label="向前移动第 2 帧"]').click();page.wait_for_function('SequenceEditor.ready()')
            assert page.evaluate('SequenceEditor.frames()[0].kind')=='custom'
            page.locator('[aria-label="删除第 3 帧"]').click();page.wait_for_function('SequenceEditor.ready()')
            # Drag fixed frame before custom frame, then restore custom-first with arrow.
            page.locator('.sequence-card').nth(1).drag_to(page.locator('.sequence-card').nth(0))
            page.wait_for_function('SequenceEditor.ready() && SequenceEditor.frames()[0].kind === "fixed"')
            page.locator('[aria-label="向前移动第 2 帧"]').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('[aria-label="编辑第 1 帧"]').click()
            expected=page.evaluate('SequenceEditor.frames()');assert [e['duration'] for e in expected]==[180,80]
            url=page.locator('#motion-image').get_attribute('src')
            preview=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
            w,h=preview.size
            assert w>64 and h>=96
            for kind,size in [('frame',(w,h)),('sheet',(w*2,h)),('gif',(w,h))]:
                with page.expect_download() as event:page.locator(f'[data-export={kind}]').click()
                dest=output/event.value.suggested_filename;event.value.save_as(dest)
                with Image.open(dest) as im:
                    assert im.size==size
                    if kind=='frame':assert im.convert('RGBA').tobytes()==preview.tobytes()
                    if kind=='gif':
                        assert im.n_frames==2
                        for i,duration in enumerate((180,80)):im.seek(i);assert im.info['duration']==duration
            page.screenshot(path=str(output/'desktop.png'),full_page=True)
            # Base changes preserve descriptors and invalidate all old generated previews.
            page.locator('#base-tab').click();page.locator('[aria-label="下一个发型"]').click()
            assert not page.locator('#animation-content').is_visible()
            assert page.evaluate('SequenceEditor.frames()')==expected
            page.wait_for_function("!document.querySelector('#generate').disabled")
            page.locator('#generate').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('[data-action=custom]').click()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output/'phone.png'),full_page=True)
            # Saved descriptors survive refresh and can be regenerated against new appearance.
            page.reload();page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.evaluate('SequenceEditor.frames()')==expected
            page.locator('#generate').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('#sequence-clear').click()
            assert page.locator('.sequence-card').count()==0
            assert not page.evaluate('SequenceEditor.ready()')
            assert not errors,errors
            browser.close();print('PASS: accessory/Extra_73 controls, fixed+custom frames, arm editing, copy/delete/button+drag ordering, durations, PNG/GIF export, invalidation, persistence, mobile layout.')
    finally:server.shutdown()


if __name__=='__main__':main()
