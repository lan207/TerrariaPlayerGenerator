"""Layer transforms in the shared 64px-wide character coordinate system.

Positive angles turn clockwise. Local transforms precede facing; whole-body
transforms use screen coordinates. Origins survive padding across a timeline.
"""
import math
from functools import lru_cache
from PIL import Image

IDENTITY = (1, 0, 0, 1, 0, 0)
PIVOTS = {'head': (32, 42), 'body': (32, 52), 'legs': (32, 64), 'whole': (32, 52)}


def scale2x(image):
    """Edge-aware 2x enlargement using only existing RGBA colours."""
    w, h = image.size
    pixels = image.load()
    out = Image.new('RGBA', (w * 2, h * 2))
    target = out.load()
    for y in range(h):
        for x in range(w):
            e = pixels[x, y]
            b = pixels[x, max(0, y - 1)]
            d = pixels[max(0, x - 1), y]
            f = pixels[min(w - 1, x + 1), y]
            hh = pixels[x, min(h - 1, y + 1)]
            children = (e, e, e, e)
            if b != hh and d != f:
                children = (d if d == b else e, f if b == f else e,
                            d if d == hh else e, f if hh == f else e)
            for i, color in enumerate(children):
                target[x * 2 + i % 2, y * 2 + i // 2] = color
    return out


@lru_cache(maxsize=24)
def rotsprite_source(size, pixels):
    """RotSprite core: three Scale2x passes before nearest rotation/reduction.

    Exact colour comparisons match the offline renderer. No fuzzy matching,
    offset search or isolated-pixel restoration is performed.
    """
    sprite = Image.frombytes('RGBA', size, pixels)
    # Transparent RGB has no visible meaning; compare it consistently with
    # the offline compositor, which initializes transparent pixels to zero.
    sprite.putdata([p if p[3] else (0, 0, 0, 0) for p in sprite.getdata()])
    for _ in range(3):
        sprite = scale2x(sprite)
    return sprite


def needs_rotsprite(matrix):
    # Quarter turns and mirrors already preserve the source pixel grid.
    return any(abs(v - round(v)) > 1e-12 for v in matrix[:4])


def rotsprite_affine(sprite, size, matrix, origin):
    """Sample final pixel centres with the same boundary rule as JavaScript."""
    box = sprite.getbbox()
    source = rotsprite_source(sprite.size, sprite.tobytes())
    pixels = source.load()
    out = Image.new('RGBA', size)
    target = out.load()
    a,b,c,d,e,f = matrix
    left,top = origin
    det = a*d-b*c
    points = [(a*x+c*y+e,b*x+d*y+f)
              for x in (box[0],box[2]) for y in (box[1],box[3])]
    x0 = max(left, math.floor(min(x for x,y in points)))
    y0 = max(top, math.floor(min(y for x,y in points)))
    x1 = min(left+size[0], math.ceil(max(x for x,y in points)))
    y1 = min(top+size[1], math.ceil(max(y for x,y in points)))
    for y in range(y0,y1):
        for x in range(x0,x1):
            px,py = x+0.5-e,y+0.5-f
            # Tiny floating-point errors at exact boundaries (e.g. 45 degrees)
            # must not choose different source pixels in Pillow and WebView.
            sx = math.floor(8*(d*px-c*py)/det+1e-9)
            sy = math.floor(8*(-b*px+a*py)/det+1e-9)
            if 0 <= sx < source.width and 0 <= sy < source.height:
                color = pixels[sx,sy]
                if color[3]: target[x-left,y-top] = color
    return out


def multiply(a, b):
    A,B,C,D,E,F = a
    a,b,c,d,e,f = b
    return (A*a+C*b, B*a+D*b, A*c+C*d, B*c+D*d, A*e+C*f+E, B*e+D*f+F)


def rotation(value, pivot):
    angle = math.radians(value.get('angle', 0))
    c,s = round(math.cos(angle), 14), round(math.sin(angle), 14)
    x,y = pivot
    return c,s,-s,c,x-c*x+s*y+value.get('x',0),y-s*x-c*y+value.get('y',0)


def layer_matrix(pose, part, arm, bob, direction):
    pose = pose or {}
    m = IDENTITY
    arm_data = pose.get((arm or '')+'_arm', {})
    if arm_data.get('enabled'):
        m = rotation(arm_data, (27,52+bob) if arm=='front' else (38,54+bob))
        if arm=='front': m = multiply((1,0,0,1,1,1),m)
    m = multiply(rotation(pose.get(part+'_transform',{}),PIVOTS[part]),m)
    if direction==-1: m = multiply((-1,0,0,1,64,0),m)
    return multiply(rotation(pose.get('whole_transform',{}),PIVOTS['whole']),m)


def render_layers(layers, pose, direction, bob, height):
    prepared=[]
    bounds=[0,0,64,height]
    for sprite,x,y,part,arm in layers:
        box=sprite.getbbox()
        if not box: continue
        m=layer_matrix(pose,part,arm,bob,direction)
        m=multiply(m,(1,0,0,1,x,y))
        # Composite adjacent layers that rotate together before Scale2x, so
        # skin/clothing boundaries are processed as a single visible sprite.
        if prepared and needs_rotsprite(m) and prepared[-1][1] == m:
            previous, _ = prepared.pop()
            merged = Image.new('RGBA', (max(previous.width, sprite.width),
                                        max(previous.height, sprite.height)))
            merged.alpha_composite(previous)
            merged.alpha_composite(sprite)
            sprite = merged
            box = sprite.getbbox()
        a,b,c,d,e,f=m
        points=[(a*px+c*py+e,b*px+d*py+f) for px in (box[0],box[2]) for py in (box[1],box[3])]
        bounds=[min(bounds[0],math.floor(min(p[0] for p in points))),
                min(bounds[1],math.floor(min(p[1] for p in points))),
                max(bounds[2],math.ceil(max(p[0] for p in points))),
                max(bounds[3],math.ceil(max(p[1] for p in points)))]
        prepared.append((sprite,m))
    transforms = pose and any(pose.get(part+'_transform',{}).get(k,0) for part in ('head','body','legs','whole') for k in ('angle','x','y'))
    if not transforms and not any(pose and pose.get(s+'_arm',{}).get('angle',0) for s in ('front','back')):
        bounds=[0,0,64,height]
    left,top,right,bottom=bounds
    image=Image.new('RGBA',(right-left,bottom-top))
    for sprite,(a,b,c,d,e,f) in prepared:
        if needs_rotsprite((a,b,c,d)):
            image.alpha_composite(rotsprite_affine(sprite,image.size,(a,b,c,d,e,f),(left,top)))
            continue
        det=a*d-b*c
        e-=left;f-=top
        inverse=(d/det,-c/det,(c*f-d*e)/det,-b/det,a/det,(b*e-a*f)/det)
        image.alpha_composite(sprite.transform(image.size,Image.Transform.AFFINE,inverse,Image.Resampling.NEAREST))
    image.info['origin']=(left,top)
    return image
