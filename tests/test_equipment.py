import unittest
from io import BytesIO

from PIL import Image, ImageChops
from equipment import equipment_catalog, in_set, matched, shoulder_offset, equipped_textures
from TrueTerrariaGenerator import TerrariaCharacterGenerator
from web_server import DEFAULTS, configuration, render_frames, sheet, gif


class EquipmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.generator = TerrariaCharacterGenerator()

    def render(self, **config):
        return self.generator.compose(**configuration(config)[1])

    def test_catalog_is_based_on_present_files_and_excludes_back_components(self):
        catalog=equipment_catalog()
        self.assertEqual({s:len(es) for s,es in catalog.items()}, {'head':274,'body':189,'legs':235})
        self.assertNotIn(246,[e['id'] for e in catalog['head']])
        self.assertEqual(next(e for e in catalog['head'] if e['id']==1)['name'],'铜头盔')

    def test_source_rule_examples(self):
        self.assertTrue(in_set('head','DrawHatHair',14))
        self.assertTrue(in_set('head','DrawFullHair',10))
        self.assertFalse(in_set('head','DrawHead',38))
        self.assertEqual(matched(201,15,1,True),(202,15,88))
        self.assertEqual(matched(0,0,83,False),(0,0,117))
        self.assertEqual(shoulder_offset(55,7),-4)
        self.assertEqual(shoulder_offset(204,16),2)

    def test_bad_equipment_is_rejected(self):
        for value in [-1,9999,True,'1',1.5]:
            with self.subTest(value=value), self.assertRaises(ValueError): configuration({'armor_head':value})
        self.assertEqual(configuration({'armor_legs':140})[0]['armor_legs'],140)
        with self.assertRaises(ValueError): configuration({'armor_head':246})

    def test_closed_helmet_hides_hair_and_hat_chooses_alt_automatically(self):
        self.assertEqual(self.render(armor_head=1,hair_color='#ff0000').tobytes(),
                         self.render(armor_head=1,hair_color='#00ff00').tobytes())
        self.assertEqual(self.render(armor_head=14,alt_hair=False).tobytes(),
                         self.render(armor_head=14,alt_hair=True).tobytes())
        self.assertNotEqual(self.render(armor_head=10,hair_color='#ff0000').tobytes(),
                            self.render(armor_head=10,hair_color='#00ff00').tobytes())

    def test_armor_replaces_clothes_and_robe_overrides_legs(self):
        a=self.render(armor_body=1,armor_legs=1)
        b=self.render(armor_body=1,armor_legs=1,shirt_color='#ff0000',undershirt_color='#00ff00',pants_color='#ffffff',shoes_color='#ffffff')
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertEqual(self.render(armor_body=15,armor_legs=1).tobytes(),self.render(armor_body=15,armor_legs=2).tobytes())
        self.assertIn('Armor_Legs_88.png',equipped_textures(DEFAULTS|{'armor_body':15})['legs'])
        self.assertIn('Armor_Legs_171.png',equipped_textures(DEFAULTS|{'armor_body':52})['body'])

    def test_unarmored_size_and_equipped_mirror(self):
        before=self.render()
        right=self.render(armor_head=14,armor_body=15,armor_legs=1)
        left=self.render(armor_head=14,armor_body=15,armor_legs=1,direction=-1)
        self.assertEqual(right.size,(64,80))
        self.assertEqual(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(),left.tobytes())
        self.assertEqual(before.size,(40,56))
        self.assertEqual(before.tobytes(),self.render(armor_head=0,armor_body=0,armor_legs=0).tobytes())

    def test_equipped_sheet_and_gif_geometry(self):
        frames=render_frames(self.generator,configuration({'armor_head':259,'armor_body':1})[1],'walk')
        self.assertEqual(len(frames),13)
        self.assertEqual(sheet(frames).size,(64*13,80))
        self.assertEqual(sheet(frames).crop((64*12,0,64*13,80)).tobytes(),frames[-1].tobytes())
        with Image.open(BytesIO(gif(frames,140,2))) as image:
            self.assertEqual(image.size,(128,160));self.assertEqual(image.n_frames,13)
            self.assertEqual(image.info['duration'],140);self.assertEqual(image.info['loop'],0)
            for i in range(13): image.seek(i); image.load()
        # Rabbit ears extend above the old 40x56 rectangle, but fit inside the margin.
        bounds=frames[0].getbbox()
        self.assertGreater(bounds[1],0);self.assertLess(bounds[1],24)

    def test_all_available_equipment_both_bodies_and_animation_extremes(self):
        checked=0
        for slot,entries in equipment_catalog().items():
            for entry in entries:
                if not entry['available']: continue
                for variant in (0,4):
                    options=configuration({'armor_'+slot:entry['id'],'skin_variant':variant})[1]
                    for action,frame in [('idle',0),('jump',0),('walk',12),('use',2)]:
                        with self.subTest(slot=slot,id=entry['id'],variant=variant,action=action):
                            result=self.generator.compose(**options,action=action,action_frame=frame)
                            self.assertEqual(result.size,(64,96) if slot=='legs' and entry['id']==140 else (64,80));self.assertIsNotNone(result.getbbox())
                            checked+=1
        print(f'Equipment coverage: {checked} rendered frames')


if __name__=='__main__': unittest.main()
