"""Verify color controls, persistence, invalidation and actual tinted exports."""
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
    out=ROOT/'test-artifacts/dyes';out.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            def preview_ready():page.wait_for_function("!document.querySelector('#generate').disabled")
            def color(id,value):page.locator(id).fill(value);page.locator(id).press('Tab');preview_ready()
            preview_ready()
            page.locator('#armor-head').select_option('1');page.locator('#armor-body').select_option('24');page.locator('#armor-legs').select_option('1');preview_ready()
            original=page.locator('#base-image').get_attribute('src')
            color('#hex-dye-armor-head','#FF6040');color('#hex-dye-armor-body','4080FF');color('#hex-dye-armor-legs','#40FF80')
            tinted=page.locator('#base-image').get_attribute('src');assert original!=tinted
            assert page.locator('#pick-dye-armor-body').input_value()=='#4080ff'
            color('#hex-dye-armor-body','badhex');assert page.locator('#hex-dye-armor-body').input_value()=='#4080FF'
            page.locator('#accessory-tab').click();page.locator('#accessory-slot').select_option('back')
            assert page.locator('#pick-dye-accessory').input_value()=='#4080ff' # Auto cape inherits body.
            color('#hex-dye-accessory','#FFFFFF');assert page.locator('#pick-dye-accessory').input_value()=='#ffffff'
            page.locator('#reset-dye-accessory').click();preview_ready()
            assert page.locator('#pick-dye-accessory').input_value()=='#4080ff'
            page.locator('#accessory-item').select_option('1');color('#hex-dye-accessory','#FF0088')
            page.locator('#accessory-slot').select_option('balloon');page.locator('#accessory-item').select_option('1')
            page.locator('#pick-dye-accessory').evaluate("e=>{e.value='#20ff80';e.dispatchEvent(new Event('input',{bubbles:true}));}");preview_ready()
            page.locator('#accessory-slot').select_option('back');assert page.locator('#pick-dye-accessory').input_value()=='#ff0088'
            page.reload();preview_ready()
            assert page.locator('#pick-dye-armor-body').input_value()=='#4080ff'
            page.locator('#accessory-tab').click();assert page.locator('#pick-dye-accessory').input_value()=='#ff0088'
            page.locator('#generate').click();page.locator('#animation-content').wait_for(state='visible')
            page.locator('#sequence-add-custom').click();page.wait_for_function('SequenceEditor.ready()')
            old=page.locator('#motion-image').get_attribute('src')
            page.locator('#gear-tab').click();color('#hex-dye-armor-body','#8844FF')
            assert not page.locator('#animation-content').is_visible()
            page.locator('#generate').click();page.wait_for_function('SequenceEditor.ready()')
            page.locator('[data-action=custom]').click()
            url=page.locator('#motion-image').get_attribute('src');assert url!=old
            expected=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
            for kind in ('frame','sheet','gif'):
                with page.expect_download() as event:page.locator(f'[data-export={kind}]').click()
                dest=out/event.value.suggested_filename;event.value.save_as(dest)
                with Image.open(dest) as image:
                    assert image.size==expected.size
                    if kind!='gif':assert image.convert('RGBA').tobytes()==expected.tobytes()
                    else:assert image.convert('RGBA').getchannel('A').tobytes()==expected.getchannel('A').tobytes()
            page.locator('#reset-dye-armor-head').click();preview_ready();assert page.locator('#pick-dye-armor-head').input_value()=='#ffffff'
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out/'phone.png'),full_page=True)
            response=page.request.post(f'http://127.0.0.1:{server.server_port}/api/preview',data={'config':{'armor_dyes':{'head':'oops'}}})
            assert response.status==400
            assert not errors,errors
            browser.close();print('PASS: equipment/accessory pickers, HEX validation, automatic cape inheritance/override/reset, per-slot persistence, timeline invalidation, PNG/GIF exports, phone layout.')
    finally:server.shutdown()

if __name__=='__main__':main()
