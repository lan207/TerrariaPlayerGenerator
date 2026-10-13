"""Rotation regressions: palette, pixel grid and composite clothing edges."""
import unittest
from PIL import Image
from poses import validate_pose
from transforms import render_layers, scale2x


class RotSpriteTests(unittest.TestCase):
    def setUp(self):
        self.sprite=Image.new('RGBA',(8,8))
        for x,y in [(2,2),(3,2),(2,3),(3,3),(4,3),(3,4),(4,4)]:
            self.sprite.putpixel((x,y),(220,120,40,255))

    def test_scale2x_keeps_palette_and_softens_diagonal_steps(self):
        scaled=scale2x(self.sprite)
        self.assertEqual(scaled.size,(16,16))
        self.assertLessEqual(set(scaled.getdata()),set(self.sprite.getdata()))
        self.assertNotEqual(scaled.tobytes(),self.sprite.resize((16,16),Image.Resampling.NEAREST).tobytes())

    def test_quarter_turns_and_mirrors_keep_nearest_pixels(self):
        for angle in (0,90,-90,180):
            for direction in (1,-1):
                pose=validate_pose({'whole_transform':{'angle':angle}})
                image=render_layers([(self.sprite,28,48,'body',None)],pose,direction,0,80)
                from transforms import multiply,layer_matrix
                a,b,c,d,e,f=multiply(layer_matrix(pose,'body',None,0,direction),(1,0,0,1,28,48))
                left,top=image.info['origin'];e-=left;f-=top;det=a*d-b*c
                inverse=(d/det,-c/det,(c*f-d*e)/det,-b/det,a/det,(b*e-a*f)/det)
                reference=self.sprite.transform(image.size,Image.Transform.AFFINE,inverse,Image.Resampling.NEAREST)
                self.assertEqual(image.tobytes(),reference.tobytes())

    def test_rotating_adjacent_skin_and_clothes_matches_composite_sprite(self):
        clothing=Image.new('RGBA',self.sprite.size)
        for x in (2,3): clothing.putpixel((x,2),(70,140,190,255))
        combined=self.sprite.copy();combined.alpha_composite(clothing)
        for angle in (-23,137):
            for direction in (1,-1):
                pose=validate_pose({'back_arm':{'angle':angle}})
                separate=render_layers([(self.sprite,12,24,'body','back'),
                                        (clothing,12,24,'body','back')],pose,direction,0,80)
                merged=render_layers([(combined,12,24,'body','back')],pose,direction,0,80)
                self.assertEqual(separate.tobytes(),merged.tobytes())
                self.assertEqual(separate.info['origin'],merged.info['origin'])
                self.assertLessEqual(set(merged.getdata()),set(combined.getdata()))


if __name__=='__main__': unittest.main()
