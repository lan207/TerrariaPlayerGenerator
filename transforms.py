"""Layer transforms in the shared 64px-wide character coordinate system.

Positive angles turn clockwise. Local transforms precede facing; whole-body
transforms use screen coordinates. Origins survive padding across a timeline.
"""
import math
from PIL import Image

IDENTITY = (1, 0, 0, 1, 0, 0)
PIVOTS = {'head': (32, 42), 'body': (32, 52), 'legs': (32, 64), 'whole': (32, 52)}


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
        det=a*d-b*c
        e-=left;f-=top
        inverse=(d/det,-c/det,(c*f-d*e)/det,-b/det,a/det,(b*e-a*f)/det)
        image.alpha_composite(sprite.transform(image.size,Image.Transform.AFFINE,inverse,Image.Resampling.NEAREST))
    image.info['origin']=(left,top)
    return image
