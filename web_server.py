"""Local web editor. Run: python web_server.py (Pillow is the only dependency)."""
from __future__ import annotations

import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import re
import traceback
import webbrowser
from urllib.parse import urlparse

from PIL import Image
from TrueTerrariaGenerator import ROOT, TerrariaCharacterGenerator, USE_FRAMES
from equipment import equipment_catalog, validate_equipment, equipped_textures
import accessories
import dyes
from poses import ACTIONS, LEGACY_ACTIONS, FRAMES, DEFAULT_POSE, STRETCHES, MAX_SEQUENCE, validate_sequence, render_sequence, bounded

WEB = ROOT / 'web'
VARIANTS = ['经典男装', '休闲男装', '正装男装', '长外套男装', '经典女装',
            '休闲女装', '正装女装', '长外套女装', '长裙男装', '长裙女装']
DEFAULTS = dict(hair=1, alt_hair=False, skin_variant=0, pants_variant=0,
                shoes_variant=0, direction=1, use_style=1, aim_angle=0,
                armor_head=0, armor_body=0, armor_legs=0,
                accessories={}, auto_capes=True,
                armor_dyes={}, accessory_dyes={},
                skin_color='#ffcca0', hair_color='#5a371e', eye_color='#325064',
                shirt_color='#508cbe', undershirt_color='#91aab9',
                pants_color='#465a96', shoes_color='#5a412d')


def png(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def data_url(image):
    return 'data:image/png;base64,' + base64.b64encode(png(image)).decode('ascii')


def integer(value, minimum, maximum, name):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} 必须为 {minimum}–{maximum} 的整数')
    return value


def configuration(raw):
    if not isinstance(raw, dict) or set(raw) - DEFAULTS.keys():
        raise ValueError('人物配置包含未知字段')
    config = DEFAULTS | raw
    options = dict(config)
    for key in ('skin_variant', 'pants_variant', 'shoes_variant'):
        integer(config[key], 0, 9, key)
    integer(config['hair'], 1, 165, '发型')
    bounded(config['aim_angle'],-180,180,'瞄准角度')
    for slot in ('head', 'body', 'legs'):
        validate_equipment(slot, config['armor_'+slot])
    config['accessories']=accessories.validate(config['accessories'])
    options['accessories']=config['accessories']
    for key, slots in [('armor_dyes', ('head','body','legs')), ('accessory_dyes', accessories.SLOTS)]:
        config[key]=dyes.validate(config[key],slots)
        options[key]=config[key]
    if type(config['auto_capes']) is not bool: raise ValueError('无效的配套披风设置')
    if type(config['alt_hair']) is not bool or type(config['direction']) is not int or config['direction'] not in (-1, 1):
        raise ValueError('无效的发型模式或朝向')
    if type(config['use_style']) is not int or config['use_style'] not in USE_FRAMES:
        raise ValueError('不支持的物品使用方式')
    for key in config:
        if key.endswith('_color'):
            value = config[key]
            if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                raise ValueError(f'{key} 必须为 #RRGGBB')
            options[key] = tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
    return config, options


def texture_names(generator, config):
    variant = config['skin_variant']
    def names(pieces, style=variant):
        return [generator.texture_name(style, p) for p in pieces]
    from equipment import in_set, matched
    head, body, _ = matched(config['armor_head'], config['armor_body'], config['armor_legs'], variant in (4,5,6,7,9))
    equipped_accessories=accessories.effective(config['accessories'],body,variant in (4,5,6,7,9),config['auto_capes'])
    alt = in_set('head', 'DrawHatHair', head) if head else config['alt_hair']
    return dict(hair=[f"Player_Hair{'Alt' if alt else ''}_{config['hair']}.png"],
                skin=names((0, 3, 5, 7, 10)), eyes=names((1, 2)),
                shirt=names((6, 13) + ((14,) if variant in (3, 7, 8) else ())),
                undershirt=names((4, 8)), pants=names((11,), config['pants_variant']),
                shoes=names((12,), config['shoes_variant']),
                equipment=equipped_textures(config), accessories={slot:accessories.path(ROOT/'Assets',slot,n).name for slot,n in equipped_accessories.items()},
                accessory_dye_sources=accessories.dye_sources(config['accessories'],equipped_accessories))


def render_frames(generator, options, action):
    if action not in FRAMES and action!='use':
        raise ValueError('未知动作')
    return [generator.compose(action=action, action_frame=i, **options)
            for i in range(len(generator.action_frames(action, options['use_style']))) ]


def sheet(frames):
    width, height = frames[0].size
    result = Image.new('RGBA', (width * len(frames), height))
    for i, frame in enumerate(frames):
        result.alpha_composite(frame, (width * i, 0))
    return result


def gif(frames, interval, scale):
    # A shared palette with index 255 reserved for transparency prevents trails,
    # black backgrounds and color changes between frames.
    palette = sheet(frames).convert('RGB').quantize(colors=255, dither=Image.Dither.NONE)
    result = []
    for frame in frames:
        frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        indexed = frame.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE)
        indexed.paste(255, mask=frame.getchannel('A').point(lambda a: 255 if a < 128 else 0))
        result.append(indexed)
    buffer = BytesIO()
    result[0].save(buffer, format='GIF', save_all=True, append_images=result[1:],
                   duration=interval, loop=0, transparency=255, disposal=2, optimize=False)
    return buffer.getvalue()


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, data, content_type, status=200, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode('utf-8'),
                        'application/json; charset=utf-8', status)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/catalog':
            hairs = sorted(int(p.stem.rsplit('_', 1)[1]) for p in (ROOT / 'Assets/Hair').glob('Player_Hair_*.png'))
            self.json(dict(defaults=DEFAULTS, hairs=hairs, variants=VARIANTS, actions=ACTIONS,
                           legacy_actions=LEGACY_ACTIONS, aiming=True,
                           use_styles=list(USE_FRAMES), equipment=equipment_catalog(), accessories=accessories.catalog(), dyes=True,
                           sequence=dict(default_pose=DEFAULT_POSE,stretches=STRETCHES,max_frames=MAX_SEQUENCE,
                                         frame_counts={a:len(f) for a,f in FRAMES.items()})))
        elif path in ('/', '/index.html', '/app.js', '/aim.js', '/sequence.js', '/style.css', '/advanced.css'):
            name = 'index.html' if path == '/' else path[1:]
            mime = {'html': 'text/html', 'js': 'text/javascript', 'css': 'text/css'}[name.rsplit('.', 1)[1]]
            self.send_bytes((WEB / name).read_bytes(), mime + '; charset=utf-8')
        else:
            self.json({'error': 'Not found'}, 404)

    def do_POST(self):
        try:
            origin = self.headers.get('Origin')
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.json({'error': '请在本地编辑器页面发起请求'}, 403)
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 262144:
                raise ValueError('无效的请求大小')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('无效的请求格式')
            config, options = configuration(body.get('config', {}))
            generator = TerrariaCharacterGenerator()
            path = urlparse(self.path).path
            if path == '/api/preview':
                image = generator.compose(**options)
                self.json(dict(image=data_url(image), width=image.width, height=image.height,
                               textures=texture_names(generator, config)))
            elif path == '/api/generate':
                frames = {action:render_frames(generator,options,action) for action in ACTIONS}
                sizes = {action:list(images[0].size) for action,images in frames.items()}
                self.json(dict(animations={action:[data_url(im) for im in images] for action,images in frames.items()},
                               sizes=sizes,width=sizes['idle'][0],height=sizes['idle'][1]))
            elif path == '/api/sequence':
                sequence=validate_sequence(body.get('sequence'))
                frames=render_sequence(generator,options,sequence)
                self.json(dict(images=[data_url(im) for im in frames],sequence=sequence,
                               width=frames[0].width,height=frames[0].height))
            elif path == '/api/action':
                images=render_frames(generator,options,body.get('action'))
                self.json(dict(images=[data_url(im) for im in images],width=images[0].width,height=images[0].height))
            elif path == '/api/export':
                action = body.get('action', 'idle')
                sequence=validate_sequence(body.get('sequence')) if action=='custom' else None
                frames = render_sequence(generator,options,sequence) if sequence else render_frames(generator, options, action)
                scale = integer(body.get('scale', 1), 1, 8, '导出倍率')
                interval = integer(body.get('interval', 100), 20, 2000, '播放间隔')
                kind = body.get('kind')
                if frames[0].width*frames[0].height*scale*scale*(1 if kind=='frame' else len(frames))>40_000_000:
                    raise ValueError('导出尺寸过大，请降低倍率或减少帧数')
                if kind == 'gif':
                    durations=[entry['duration'] for entry in sequence] if sequence else interval
                    self.send_bytes(gif(frames, durations, scale), 'image/gif', filename=f'player_{action}.gif')
                elif kind in ('frame', 'sheet'):
                    current = integer(body.get('frame', 0), 0, len(frames)-1, '当前帧')
                    im = frames[current] if kind == 'frame' else sheet(frames)
                    im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
                    self.send_bytes(png(im), 'image/png', filename=f'player_{action}_{kind}.png')
                else:
                    raise ValueError('未知导出类型')
            else:
                self.json({'error': 'Not found'}, 404)
        except (ValueError, TypeError, KeyError, FileNotFoundError) as error:
            self.json({'error': str(error)}, 400)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            traceback.print_exc()
            self.json({'error': '生成失败，请查看服务端终端中的错误'}, 500)


def main():
    parser = argparse.ArgumentParser(description='Terraria local player editor')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='Open the editor in the default browser')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Player Studio: http://127.0.0.1:{server.server_port}  (Ctrl+C to stop)', flush=True)
    if args.open:
        webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
