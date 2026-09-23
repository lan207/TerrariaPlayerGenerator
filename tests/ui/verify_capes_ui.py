"""Winter cape pairing, dye inheritance, and preview/export regression check."""
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
    output=ROOT/'test-artifacts/capes';output.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            def ready():page.wait_for_function("!document.querySelector('#generate').disabled")
            ready();page.locator('#accessory-tab').click()
            page.locator('#accessory-item').select_option('6');ready()
            assert 'Acc_Back_6.png' in page.locator('#accessory-textures').inner_text()
            assert 'Acc_Front_4.png' in page.locator('#accessory-textures').inner_text()
            page.locator('#hex-dye-accessory').fill('#6090FF');page.locator('#hex-dye-accessory').press('Tab');ready()
            page.locator('#accessory-slot').select_option('front')
            assert page.locator('#accessory-item option').first.inner_text()=='自动配套：冬季披风'
            assert page.locator('#pick-dye-accessory').input_value()=='#6090ff'
            page.locator('#hex-dye-accessory').fill('#FF9060');page.locator('#hex-dye-accessory').press('Tab');ready()
            assert page.locator('#pick-dye-accessory').input_value()=='#ff9060'
            page.locator('#reset-dye-accessory').click();ready()
            assert page.locator('#pick-dye-accessory').input_value()=='#6090ff'
            page.locator('[data-direction="-1"]').click();ready()
            url=page.locator('#base-image').get_attribute('src')
            expected=Image.open(BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')
            page.locator('#generate').click();page.locator('#animation-content').wait_for(state='visible')
            with page.expect_download() as event:page.locator('[data-export=frame]').click()
            target=output/'winter-cape-export.png';event.value.save_as(target)
            with Image.open(target) as image:assert image.convert('RGBA').tobytes()==expected.tobytes()
            page.locator('#accessory-clear').click();ready()
            assert page.locator('#accessory-textures').inner_text()=='无可见饰品'
            page.locator('#accessory-item').select_option('4');ready() # Selecting the front also completes the back.
            assert 'Acc_Back_6.png' in page.locator('#accessory-textures').inner_text()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output/'phone.png'),full_page=True)
            assert not errors,errors
            browser.close();print('PASS: WinterCape front/back pairing, automatic label, inherited/overridden/reset dyes, left-facing preview=PNG export, removal, phone layout.')
    finally:server.shutdown()

if __name__=='__main__':main()
