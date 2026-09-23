"""Smoke-test shared desktop UI and Android bridge dispatch in headless Chrome."""
import base64
from functools import partial
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / '.test-tools')]
from PIL import Image
from playwright.sync_api import sync_playwright
from mobile.prepare import prepare
from tests.mobile.verify_offline import QuietHandler
from web_server import Handler


def main():
    mobile = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(prepare())))
    desktop = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    for server in (mobile,desktop): Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':360,'height':800})
            requests=[]
            page.on('request',lambda request:requests.append(request.url))
            page.goto(f'http://127.0.0.1:{mobile.server_port}')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            page.locator('#base-tab').click()
            page.locator('[aria-label="下一个发型"]').click()
            page.reload()
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator('#value-hair').inner_text()=='发型 2'
            # Mock only the Java interface to verify the exact bytes/metadata sent by JS.
            page.evaluate('window.AndroidFiles={save:(name,mime,data)=>window.savedFile={name,mime,data}}')
            page.locator('#generate').click()
            page.locator('#animation-content').wait_for(state='visible')
            page.locator('#interval').fill('2000')
            page.locator('[data-export=gif]').click()
            page.wait_for_function('window.savedFile !== undefined')
            saved=page.evaluate('window.savedFile')
            assert saved['name']=='player_idle_gif.gif' and saved['mime']=='image/gif'
            image=Image.open(BytesIO(base64.b64decode(saved['data'])))
            assert image.size==(40,56) and image.n_frames==1 and image.info['duration']==2000
            assert all(url.startswith(f'http://127.0.0.1:{mobile.server_port}/') and '/api/' not in url for url in requests)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            # Shared app.js must still talk to the Python server on desktop.
            page=browser.new_page(viewport={'width':1280,'height':900})
            page.goto(f'http://127.0.0.1:{desktop.server_port}')
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.evaluate('window.LocalPlayer === undefined')
            page.locator('#generate').click()
            page.locator('#animation-content').wait_for(state='visible')
            page.locator('[data-action=walk]').click()
            with page.expect_download() as result: page.locator('[data-export=sheet]').click()
            with Image.open(result.value.path()) as image:
                assert image.size==(520,56)
            browser.close()
            print('PASS: persisted appearance, Android export bridge bytes, single-frame GIF, no mobile API/network dependency, desktop generation/export.')
    finally:
        mobile.shutdown();desktop.shutdown()


if __name__ == '__main__': main()
