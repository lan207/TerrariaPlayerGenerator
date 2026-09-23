from copy import deepcopy
from io import BytesIO
import math
import unittest
from PIL import Image
import accessories
from equipment import equipped_textures
from poses import DEFAULT_POSE, STRETCHES, ACTIONS, validate_pose, validate_sequence, render_sequence
from TrueTerrariaGenerator import TerrariaCharacterGenerator
from web_server import configuration, render_frames, sheet, gif


class PoseAccessoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.g=TerrariaCharacterGenerator()

    def test_all_accessory_textures_and_custom_arm_frames(self):
        count=0
        for slot,group in accessories.catalog().items():
            for item in group['items']:
                for variant in (0,4):
                    options=configuration({'skin_variant':variant,'accessories':{slot:item['id']}})[1]
                    for action,frame in [('idle',0),('jump',0),('walk',12)]:
                        with self.subTest(slot=slot,item=item['id'],variant=variant,action=action):
                            image=self.g.compose(**options,action=action,action_frame=frame)
                            self.assertEqual(image.size,(64,80));self.assertIsNotNone(image.getbbox());count+=1
                    if slot in ('hand_on','hand_off'):
                        for stretch in STRETCHES:
                            pose=deepcopy(DEFAULT_POSE)
                            pose['front_arm'].update(stretch=stretch,angle=-70)
                            pose['back_arm'].update(stretch=stretch,angle=40)
                            self.assertIsNotNone(self.g.compose(**options,pose=pose).getbbox());count+=1
        print(f'Accessory coverage: {count} rendered frames')

    def test_source_composite_stretches_rotation_and_mirror(self):
        for variant in (0,4):
            for armor in (0,1,55):
                options=configuration({'skin_variant':variant,'armor_body':armor})[1]
                for stretch in STRETCHES:
                    images=[]
                    for angle in (-180,-90,-45,0,45,90,180):
                        pose=deepcopy(DEFAULT_POSE)
                        pose['front_arm'].update(stretch=stretch,angle=angle)
                        pose['back_arm'].update(stretch=stretch,angle=-angle)
                        right=self.g.compose(**options,pose=pose)
                        pose['direction']=-1
                        left=self.g.compose(**options,pose=pose)
                        self.assertEqual(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(),left.tobytes())
                        images.append(right.tobytes())
                    self.assertGreater(len(set(images)),3)
        options=configuration({})[1]
        a=deepcopy(DEFAULT_POSE);b=deepcopy(a);b['front_arm']['angle']=-90
        self.assertNotEqual(self.g.compose(**options,pose=a).tobytes(),self.g.compose(**options,pose=b).tobytes())

    def test_named_actions_have_real_composite_changes(self):
        options=configuration({})[1]
        self.assertIn('show',ACTIONS);self.assertIn('shoot',ACTIONS)
        for action,count in [('eat',4),('drink',5),('guitar',7)]:
            frames=render_frames(self.g,options,action)
            self.assertEqual(len(frames),count);self.assertGreater(len({im.tobytes() for im in frames}),1)
        self.assertNotEqual(render_frames(self.g,options,'show')[0].tobytes(),render_frames(self.g,options,'idle')[0].tobytes())

    def test_extra73_eight_frames_and_transparent_margin(self):
        options=configuration({'armor_legs':140})[1]
        results=[]
        for frame in range(8):
            pose=deepcopy(DEFAULT_POSE);pose['effect_frame']=frame
            image=self.g.compose(**options,pose=pose)
            self.assertEqual(image.size,(64,96))
            self.assertGreater(image.getbbox()[3],70)
            self.assertLess(image.getbbox()[3],96)
            results.append(image.tobytes())
        self.assertGreater(len(set(results)),1)
        self.assertEqual(equipped_textures(configuration({'armor_legs':140})[0])['legs'],['Extra_73.png'])

    def test_accessory_visibility_and_auto_capes(self):
        bare=self.g.compose(**configuration({'armor_body':24,'auto_capes':False})[1])
        cape=self.g.compose(**configuration({'armor_body':24,'auto_capes':True})[1])
        self.assertNotEqual(bare.tobytes(),cape.tobytes())
        self.assertEqual(accessories.effective({'hand_on':1,'hand_off':1},83,False,False),{})
        options=configuration({'accessories':{'face':2},'hair_color':'#ff0000'})[1]
        a=self.g.compose(**options);options['hair_color']=(0,255,0)
        self.assertEqual(a.tobytes(),self.g.compose(**options).tobytes())

    def test_sequence_order_sizes_and_variable_gif_timing(self):
        pose=deepcopy(DEFAULT_POSE);pose['front_arm']['angle']=-90
        seq=validate_sequence([{'kind':'fixed','action':'show','frame':0,'duration':70},
                               {'kind':'custom','pose':pose,'duration':190},
                               {'kind':'fixed','action':'walk','frame':4,'duration':120}])
        options=configuration({})[1];frames=render_sequence(self.g,options,seq)
        self.assertEqual([im.size for im in frames],[(64,80)]*3)
        reversed_frames=render_sequence(self.g,options,list(reversed(seq)))
        self.assertEqual([im.tobytes() for im in frames],[im.tobytes() for im in reversed(reversed_frames)])
        self.assertEqual(sheet(frames).size,(192,80))
        with Image.open(BytesIO(gif(frames,[70,190,120],2))) as animation:
            self.assertEqual(animation.n_frames,3);self.assertEqual(animation.size,(128,160))
            for i,time in enumerate((70,190,120)):
                animation.seek(i);self.assertEqual(animation.info['duration'],time)

    def test_untrusted_pose_and_sequence_inputs(self):
        for angle in [math.nan,math.inf,181,True,'45']:
            with self.subTest(angle=angle),self.assertRaises(ValueError):validate_pose({'front_arm':{'angle':angle}})
        for sequence in [[],[{'kind':'fixed','action':'unknown'}],[{'kind':'fixed','action':'idle','frame':1}],
                         [{'kind':'custom','pose':{'body_frame':20}}],[{'kind':'fixed','action':'idle','duration':23}],
                         [{'kind':'fixed','action':'idle'}]*121]:
            with self.subTest(sequence=sequence[:1]),self.assertRaises(ValueError):validate_sequence(sequence)
        for raw in [{'hand_on':999},{'face':True},{'unknown':1}]:
            with self.assertRaises(ValueError):configuration({'accessories':raw})

    def test_part_transforms_expand_frame_and_keep_timeline_origins_aligned(self):
        options=configuration({'armor_head':1,'armor_body':1,'armor_legs':1,
                               'accessories':{'back':1,'hand_on':1,'balloon':1}})[1]
        baseline=deepcopy(DEFAULT_POSE)
        turned=deepcopy(baseline)
        turned['head_transform']={'angle':37,'x':-7,'y':-3}
        turned['body_transform']={'angle':-23,'x':5,'y':4}
        turned['legs_transform']={'angle':16,'x':-2,'y':3}
        turned['whole_transform']={'angle':11,'x':48,'y':-2}
        image=self.g.compose(**options,pose=turned)
        self.assertGreater(image.width,64);self.assertGreater(image.height,80)
        self.assertEqual(image.getchannel('A').getbbox(),image.getbbox())
        seq=validate_sequence([{'kind':'custom','pose':turned,'duration':80},
                               {'kind':'custom','pose':baseline,'duration':120}])
        images=render_sequence(self.g,options,seq)
        self.assertEqual(images[0].size,images[1].size)
        self.assertEqual(images[0].info['origin'],images[1].info['origin'])
        self.assertNotEqual(images[0].tobytes(),images[1].tobytes())


if __name__=='__main__':unittest.main()
