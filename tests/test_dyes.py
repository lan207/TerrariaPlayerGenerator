from copy import deepcopy
from io import BytesIO
import unittest
from PIL import Image
import accessories
from poses import DEFAULT_POSE, validate_sequence, render_sequence
from TrueTerrariaGenerator import TerrariaCharacterGenerator
from web_server import configuration, render_frames, gif


class DyeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.g=TerrariaCharacterGenerator()

    def draw(self, config, **kwargs): return self.g.compose(**configuration(config)[1],**kwargs)

    def test_white_is_exact_identity_including_special_layers(self):
        for config in [dict(armor_head=242,armor_body=24,armor_legs=1),dict(armor_head=259,armor_body=15),
                       dict(armor_head=265,armor_body=52),dict(armor_head=274,armor_legs=140),
                       dict(accessories={slot:1 for slot in accessories.SLOTS})]:
            dyed=config|dict(armor_dyes={s:'#ffffff' for s in ('head','body','legs')},
                             accessory_dyes={s:'#ffffff' for s in accessories.SLOTS})
            for kwargs in ({},{'pose':deepcopy(DEFAULT_POSE)}):
                with self.subTest(config=config,kwargs=kwargs):
                    self.assertEqual(self.draw(config,**kwargs).tobytes(),self.draw(dyed,**kwargs).tobytes())

    def test_every_slot_changes_only_color_and_preserves_alpha(self):
        for slot in ('head','body','legs'):
            plain=self.draw({'armor_'+slot:1})
            dyed=self.draw({'armor_'+slot:1,'armor_dyes':{slot:'#000000'}})
            self.assertNotEqual(plain.tobytes(),dyed.tobytes())
            self.assertEqual(plain.getchannel('A').tobytes(),dyed.getchannel('A').tobytes())
        for slot in accessories.SLOTS:
            config={'accessories':{slot:1}}
            plain=self.draw(config);dyed=self.draw(config|{'accessory_dyes':{slot:'#000000'}})
            with self.subTest(slot=slot):
                self.assertNotEqual(plain.tobytes(),dyed.tobytes())
                self.assertEqual(plain.getchannel('A').tobytes(),dyed.getchannel('A').tobytes())
        all_black=self.draw({'armor_head':1,'armor_body':1,'armor_legs':1,
                            'armor_dyes':{s:'#000000' for s in ('head','body','legs')}})
        self.assertIn((255,204,160,255),set(all_black.getdata())) # Exposed skin is not dyed.
        self.assertEqual(self.draw({}).tobytes(),self.draw({'armor_dyes':{'head':'#123456'}}).tobytes())

    def test_robe_coat_and_automatic_cape_follow_body_with_overrides(self):
        robe={'armor_body':15,'armor_dyes':{'body':'#2040ff'}}
        self.assertEqual(self.draw(robe).tobytes(),self.draw(robe|{'armor_dyes':{'body':'#2040ff','legs':'#ff0000'}}).tobytes())
        for body in (15,52):
            plain=self.draw({'armor_body':body});dyed=self.draw({'armor_body':body,'armor_dyes':{'body':'#000000'}})
            self.assertNotEqual(plain.crop((0,64,64,80)).tobytes(),dyed.crop((0,64,64,80)).tobytes())
        config={'armor_body':24,'armor_dyes':{'body':'#804020'}}
        automatic=self.draw(config)
        explicit=self.draw(config|{'accessories':{'back':29},'accessory_dyes':{'back':'#804020'}})
        self.assertEqual(automatic.tobytes(),explicit.tobytes())
        reset_cape=self.draw(config|{'accessory_dyes':{'back':'#ffffff'}})
        self.assertNotEqual(automatic.tobytes(),reset_cape.tobytes())

    def test_extra73_balloon_and_rotated_hands(self):
        pose=deepcopy(DEFAULT_POSE);pose.update(effect_frame=3,leg_frame=1)
        pose['front_arm']['angle']=-65;pose['back_arm']['angle']=45
        for config,dye in [({'armor_legs':140},{'armor_dyes':{'legs':'#00ff00'}}),
                           ({'accessories':{'balloon':1}},{'accessory_dyes':{'balloon':'#ff0000'}}),
                           ({'accessories':{'hand_on':1,'hand_off':1}},{'accessory_dyes':{'hand_on':'#0000ff','hand_off':'#ff0000'}})]:
            plain=self.draw(config,pose=pose);colored=self.draw(config|dye,pose=pose)
            self.assertNotEqual(plain.tobytes(),colored.tobytes())
            self.assertEqual(plain.getchannel('A').tobytes(),colored.getchannel('A').tobytes())

    def test_dyes_flow_through_sequence_and_gif(self):
        config={'armor_body':1,'armor_dyes':{'body':'#2288ff'},'accessories':{'back':1},'accessory_dyes':{'back':'#ff0022'}}
        sequence=validate_sequence([{'kind':'fixed','action':'show','duration':100},
                                    {'kind':'custom','pose':deepcopy(DEFAULT_POSE),'duration':180}])
        frames=render_sequence(self.g,configuration(config)[1],sequence)
        self.assertEqual(frames[0].tobytes(),render_frames(self.g,configuration(config)[1],'show')[0].tobytes())
        with Image.open(BytesIO(gif(frames,[100,180],1))) as image:
            self.assertEqual(image.n_frames,2)
            for i in range(2):
                image.seek(i)
                self.assertEqual(image.convert('RGBA').getchannel('A').tobytes(),frames[i].getchannel('A').tobytes())

    def test_invalid_color_and_slot_rejected_and_legacy_defaults(self):
        for key,values in [('armor_dyes',[None,[],{'wings':'#ffffff'},{'head':'red'},{'body':'#123'},{'legs':True}]),
                           ('accessory_dyes',[{'head':'#ffffff'},{'back':'#12345678'},{'face':22}])]:
            for value in values:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):configuration({key:value})
        config,_=configuration({'armor_body':1})
        self.assertEqual(config['armor_dyes'],{});self.assertEqual(config['accessory_dyes'],{})
        self.assertEqual(configuration({'armor_dyes':{'head':'#AABBCC'}})[0]['armor_dyes'],{'head':'#aabbcc'})


if __name__=='__main__':unittest.main()
