import math
import unittest
from io import BytesIO
from PIL import Image
from poses import ACTIONS, LEGACY_ACTIONS, FRAMES, shooting_pose, validate_sequence, render_sequence
from web_server import configuration, render_frames, sheet, gif
from TrueTerrariaGenerator import TerrariaCharacterGenerator


class AimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=TerrariaCharacterGenerator()

    def test_common_actions_exclude_item_specific_samples(self):
        self.assertEqual(set(ACTIONS),{'idle','walk','jump','swing','show','shoot'})
        self.assertIn('guitar',LEGACY_ACTIONS)
        self.assertEqual(FRAMES['shoot'],(3,))

    def test_source_angle_thresholds_and_mouse_direction(self):
        for angle,direction,frame in [(0,1,3),(-70,1,2),(60,1,4),(180,-1,3),(-140,-1,3),(-120,-1,2),(120,-1,4),
                                      (math.degrees(-0.75)-.01,1,2),(math.degrees(-0.75)+.01,1,3),
                                      (math.degrees(.6)-.01,1,3),(math.degrees(.6)+.01,1,4)]:
            pose=shooting_pose(angle)
            with self.subTest(angle=angle):
                self.assertEqual(pose['direction'],direction);self.assertEqual(pose['body_frame'],frame)
                self.assertFalse(pose['front_arm']['enabled']);self.assertFalse(pose['back_arm']['enabled'])

    def test_continuous_angle_is_data_not_a_three_frame_animation(self):
        for angle in (-175.8,-120,-70,-12.3,0,22.7,55,110,179):
            options=configuration({'aim_angle':angle,'armor_body':1,'accessories':{'hand_on':1},'armor_dyes':{'body':'#4060ff'}})[1]
            frames=render_frames(self.g,options,'shoot')
            self.assertEqual(len(frames),1)
            self.assertEqual(sheet(frames).size,frames[0].size)
            self.assertEqual(frames[0].tobytes(),self.g.compose(**options,pose=shooting_pose(angle)).tobytes())
            with Image.open(BytesIO(gif(frames,100,1))) as image:self.assertEqual(image.n_frames,1)
        right=render_frames(self.g,configuration({'aim_angle':-25})[1],'shoot')[0]
        left=render_frames(self.g,configuration({'aim_angle':-155})[1],'shoot')[0]
        self.assertEqual(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(),left.tobytes())
        # Different angles in the same vanilla body-frame band share the player texture.
        self.assertEqual(self.g.compose(action='shoot',aim_angle=10).tobytes(),self.g.compose(action='shoot',aim_angle=20).tobytes())

    def test_saved_shoot_frames_capture_their_own_target_angle(self):
        sequence=validate_sequence([{'kind':'fixed','action':'shoot','frame':0,'aim_angle':-60,'duration':100},
                                    {'kind':'fixed','action':'shoot','frame':0,'aim_angle':120,'duration':200},
                                    {'kind':'fixed','action':'guitar','frame':2}])
        frames=render_sequence(self.g,configuration({'aim_angle':0})[1],sequence)
        changed=render_sequence(self.g,configuration({'aim_angle':45})[1],sequence)
        self.assertEqual([im.tobytes() for im in frames],[im.tobytes() for im in changed])
        self.assertNotEqual(frames[0].tobytes(),frames[1].tobytes())

    def test_invalid_angles_or_second_shoot_frame_rejected(self):
        for angle in (True,'45',math.nan,math.inf,181,-181):
            with self.subTest(angle=angle),self.assertRaises(ValueError):configuration({'aim_angle':angle})
            with self.subTest(angle=angle),self.assertRaises(ValueError):validate_sequence([{'kind':'fixed','action':'shoot','aim_angle':angle}])
        with self.assertRaises(ValueError):validate_sequence([{'kind':'fixed','action':'shoot','frame':1}])


if __name__=='__main__':unittest.main()
