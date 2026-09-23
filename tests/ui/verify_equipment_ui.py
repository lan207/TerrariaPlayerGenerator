"""End-to-end web equipment selection, invalidation, exports and responsive layout."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Thread

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.test-tools')]
from PIL import Image
from playwright.sync_api import sync_playwright
from web_server import Handler


class QuietHandler(Handler):
    def log_message(self,*_): pass


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    Thread(target=server.serve_forever,daemon=True).start()
    out=ROOT/'test-artifacts/equipment'
    out.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#equipment-panel').is_visible()
            page.locator('#search-head').fill('铜头盔')
            assert 2 <= page.locator('#armor-head option').count() < 10
            assert all('铜头盔' in text for text in page.locator('#armor-head option').all_text_contents()[1:])
            page.locator('#armor-head').select_option('1')
            page.locator('#armor-body').select_option('1')
            page.locator('#armor-legs').select_option('1')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#alt-hair').is_disabled()
            assert page.locator('.spec strong').inner_text()=='64 × 80'
            page.locator('#generate').click()
            page.locator('#animation-content').wait_for(state='visible')
            page.locator('[data-action=walk]').click()
            assert page.locator('.frame-thumb').count()==13
            for kind,size in [('frame',(64,80)),('sheet',(832,80)),('gif',(64,80))]:
                with page.expect_download() as event:page.locator(f'[data-export={kind}]').click()
                dest=out/event.value.suggested_filename;event.value.save_as(dest)
                with Image.open(dest) as image:
                    assert image.size==size
                    if kind=='gif':assert image.n_frames==13
            page.screenshot(path=str(out/'desktop.png'),full_page=True)
            # Robe hides selected leggings, clearing restores the original unarmored frame size.
            page.locator('#armor-body').select_option('15')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert not page.locator('#animation-content').is_visible()
            assert '88' in page.locator('#equipped-legs').inner_text()
            page.locator('#clear-equipment').click()
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('.spec strong').inner_text()=='40 × 56'
            assert page.locator('#armor-legs').input_value()=='0'
            assert not page.locator('#alt-hair').is_disabled()
            page.locator('#base-tab').click()
            assert page.locator('#base-options').is_visible()
            page.locator('[aria-label="下一个发型"]').click()
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#value-hair').inner_text()=='发型 2'
            page.locator('#gear-tab').click()
            page.set_viewport_size({'width':390,'height':844})
            page.locator('#armor-head').select_option('259')
            page.locator('#armor-body').select_option('15')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out/'phone.png'),full_page=True)
            response=page.request.post(f'http://127.0.0.1:{server.server_port}/api/preview',data={'config':{'armor_head':9999}})
            assert response.status==400
            assert not errors,errors
            browser.close()
            print('PASS: equipment search/selection, robe override, unload, animation invalidation, three exports, mobile layout, invalid API input.')
    finally:server.shutdown()


if __name__=='__main__':main()
