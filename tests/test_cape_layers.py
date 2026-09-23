from copy import deepcopy
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import accessories
from poses import DEFAULT_POSE, render_sequence, validate_sequence
from TrueTerrariaGenerator import TerrariaCharacterGenerator
from web_server import configuration, render_frames, texture_names, sheet, gif


class CapeLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=TerrariaCharacterGenerator()

    def draw(self,config,**kwargs):return self.g.compose(**configuration(config)[1],**kwargs)

    def test_winter_cape_is_one_accessory_with_two_texture_slots(self):
        # Item #2287: backSlot=3+2287-2284=6, frontSlot=1+2287-2284=4.
        self.assertEqual(accessories.effective({'back':6},0,False,False),{'back':6,'front':4})
        self.assertEqual(accessories.effective({'front':4},0,False,False),{'front':4,'back':6})
        self.assertEqual(accessories.effective({'back':6,'front':1},0,False,False),{'back':6,'front':1})
        for back,front in accessories.CAPE_BACK_TO_FRONT.items():
            self.assertTrue(accessories.path(Path('Assets'),'back',back).is_file())
            self.assertTrue(accessories.path(Path('Assets'),'front',front).is_file())
            self.assertEqual(accessories.effective({'back':back},0,False,False).get('front'),front)
        names=texture_names(self.g,configuration({'accessories':{'back':6}})[0])
        self.assertEqual(names['accessories'],{'back':'Acc_Back_6.png','front':'Acc_Front_4.png'})
        self.assertEqual(names['accessory_dye_sources']['front'],'back')

    def test_paired_parts_keep_their_owners_dye_and_allow_overrides(self):
        automatic={'accessories':{'back':6},'accessory_dyes':{'back':'#8040ff'}}
        explicit={'accessories':{'back':6,'front':4},'accessory_dyes':{'back':'#8040ff','front':'#8040ff'}}
        self.assertEqual(self.draw(automatic).tobytes(),self.draw(explicit).tobytes())
        self.assertNotEqual(self.draw(automatic).tobytes(),self.draw(automatic|{'accessory_dyes':{'back':'#8040ff','front':'#ffffff'}}).tobytes())
        from_front={'accessories':{'front':4},'accessory_dyes':{'front':'#8040ff'}}
        self.assertEqual(self.draw(from_front).tobytes(),self.draw(explicit).tobytes())
        self.assertEqual(accessories.dye_sources({'back':6},{'back':6,'front':4}),{'back':'back','front':'back'})

    def test_source_half_rectangles_straddle_the_front_arm(self):
        # Independent source-order oracle using opaque marker colors: torso purple,
        # front accessory source left half red/right half blue, front arm green.
        # The left half goes OVER the arm; the right half goes OVER torso but UNDER arm.
        original=self.g._open
        red=(250,0,0,255);blue=(0,0,250,255);green=(0,250,0,255);purple=(100,0,100,255)
        front=Image.new('RGBA',(40,1120));p=ImageDraw.Draw(front)
        p.rectangle((0,0,19,1119),fill=red);p.rectangle((20,0,39,1119),fill=blue)
        body=Image.new('RGBA',(360,224));p=ImageDraw.Draw(body)
        for ty in (0,2):
            p.rectangle((0,ty*56,79,ty*56+55),fill=purple) # standing/jumping torso cells
        for ay in (0,1):p.rectangle((2*40+8,ay*56+20,2*40+31,ay*56+31),fill=green)
        def fixture(path):
            if path.name in ('Acc_Front_4.png','Acc_Front_6.png'):return front
            if path.name=='Acc_Back_6.png':return Image.new('RGBA',(40,1120))
            if path.name=='Armor_1.png':return body
            return original(path)
        with patch.object(self.g,'_open',side_effect=fixture):
            for variant in (0,4):
                for direction in (1,-1):
                    for action in ('idle','jump'):
                        image=self.draw({'armor_body':1,'skin_variant':variant,'direction':direction,'accessories':{'front':4}},action=action)
                        def pixel(x,y):return image.getpixel((12+(x if direction==1 else 39-x),24+y))
                        self.assertEqual(pixel(10,25),red)
                        self.assertEqual(pixel(30,25),green)
                        self.assertEqual(pixel(30,40),blue)
            # Front #6 is explicitly in DrawsInNeckLayer only while jumping.
            ordinary=self.draw({'armor_body':1,'accessories':{'front':6}})
            jumping=self.draw({'armor_body':1,'accessories':{'front':6}},action='jump')
            self.assertEqual(ordinary.getpixel((22,49)),red)
            self.assertEqual(jumping.getpixel((22,49)),green)

    def test_real_winter_cape_left_lapel_is_visible_after_arm(self):
        src=Image.open('Assets/Accessories/Acc_Front_4.png').convert('RGBA')
        for variant in (0,4):
            for direction in (1,-1):
                for body_frame in (0,5,7,19):
                    pose=deepcopy(DEFAULT_POSE);pose.update(body_frame=body_frame,head_frame=body_frame,leg_frame=body_frame,direction=direction)
                    pose['front_arm'].update(angle=-55);pose['back_arm'].update(angle=40)
                    image=self.draw({'skin_variant':variant,'armor_body':1,'accessories':{'back':6}},pose=pose)
                    visible=0
                    for y in range(56):
                        for x in range(20):
                            color=src.getpixel((x,body_frame*56+y))
                            if color[3]==255:
                                self.assertEqual(image.getpixel((12+(x if direction==1 else 39-x),24+y)),color)
                                visible+=1
                    # Some jump/walk cells intentionally have an empty near half.
                    if body_frame==0:self.assertGreater(visible,20)

    def test_same_paired_cape_in_presets_sequences_and_exports(self):
        options=configuration({'accessories':{'back':6},'accessory_dyes':{'back':'#5080ff'}})[1]
        frames=render_frames(self.g,options,'walk')
        sequence=validate_sequence([{'kind':'fixed','action':'walk','frame':i} for i in range(13)])
        self.assertEqual([im.tobytes() for im in frames],[im.tobytes() for im in render_sequence(self.g,options,sequence)])
        self.assertEqual(sheet(frames).size,(832,80))
        with Image.open(BytesIO(gif(frames,100,1))) as animation:
            self.assertEqual(animation.n_frames,13)
            for i,frame in enumerate(frames):
                animation.seek(i)
                self.assertEqual(animation.convert('RGBA').getchannel('A').tobytes(),frame.getchannel('A').tobytes())


if __name__=='__main__':unittest.main()
