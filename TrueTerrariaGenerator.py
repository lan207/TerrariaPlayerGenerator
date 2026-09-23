"""Compose a single Terraria 1.4.4 player sprite from extracted vanilla textures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable
from functools import lru_cache

from PIL import Image
from poses import FRAMES, builtin_pose, validate_pose, shooting_pose


ROOT = Path(__file__).resolve().parent
FRAME_WIDTH = 40
FRAME_HEIGHT = 56
USE_FRAMES = {1: (1, 2, 3), 2: (3,), 3: (3,), 4: (2,), 5: (2, 3, 4),
              6: (2, 3), 7: (3, 2), 11: (4, 3, 2), 12: (3,), 13: (1, 2, 3)}
BACK_HAIR = {i + 1 for i in (51,52,53,54,55,64,65,66,67,68,69,70,71,72,73,
    78,79,80,81,82,83,84,85,86,87,90,91,92,93,94,95,96,97,98,99,101,102,103,
    105,106,107,108,109,110,111,113,114,115,133,134,146,162,6)}


class TerrariaCharacterGenerator:
    def __init__(self, assets_path: str | Path | None = None):
        self.assets_path = Path(assets_path) if assets_path else ROOT / "Assets"
        self.player_path = self.assets_path / "Player"
        self.hair_path = self.assets_path / "Hair"

    @lru_cache(maxsize=256)
    def _open(self, path: Path) -> Image.Image:
        if not path.is_file():
            raise FileNotFoundError(f"Required texture not found: {path}")
        with Image.open(path) as image:
            return image.convert("RGBA")

    @staticmethod
    def _frame(image: Image.Image, index: int, width: int = FRAME_WIDTH,
               height: int = FRAME_HEIGHT, *, columns: int = 1) -> Image.Image:
        if width <= 0 or height <= 0 or image.width % width:
            raise ValueError(f"Texture dimensions {image.size} are not aligned to {width}x{height} frames")
        cols = image.width // width
        if not 1 <= columns <= cols:
            raise ValueError(f"Requested {columns} columns from a {cols}-column texture")
        # Some extracted vanilla sheets are cropped two pixels short at the bottom.
        # Pillow's crop semantics provide the missing area as transparent pixels.
        rows = (image.height + height - 1) // height
        total = rows * columns
        if not 0 <= index < total:
            raise ValueError(f"Frame index {index} is out of range (0..{total - 1})")
        x = (index % columns) * width
        y = (index // columns) * height
        frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        frame.alpha_composite(image.crop((x, y, min(x + width, image.width), min(y + height, image.height))))
        return frame

    @staticmethod
    def recolor_image(image: Image.Image, target_color: tuple[int, int, int]) -> Image.Image:
        """Tint grayscale vanilla skin/cloth while retaining brightness and alpha."""
        rgba = image.convert("RGBA")
        pixels = rgba.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                r, g, b, alpha = pixels[x, y]
                if alpha:
                    pixels[x, y] = tuple(round(channel * tint / 255)
                                        for channel, tint in zip((r, g, b), target_color)) + (alpha,)
        return rgba

    def _texture_frame(self, name: str, index: int) -> Image.Image:
        return self._frame(self._open(self.player_path / name), index)

    def _body_cell(self, texture_name: str, cell: int) -> Image.Image:
        texture = self._open(self.player_path / texture_name)
        return self._frame(texture, cell, columns=texture.width // FRAME_WIDTH)

    def _body_cell_at(self, texture_name: str, x: int, y: int) -> Image.Image:
        texture = self._open(self.player_path / texture_name)
        columns = texture.width // FRAME_WIDTH
        rows = (texture.height + FRAME_HEIGHT - 1) // FRAME_HEIGHT
        if not 0 <= x < columns or not 0 <= y < rows:
            raise ValueError(f"Frame ({x}, {y}) is outside {texture_name} ({columns}x{rows})")
        return self._frame(texture, y * columns + x, columns=columns)

    @staticmethod
    def action_frames(action: str, use_style: int = 1) -> tuple[int, ...]:
        frames = dict(FRAMES)
        if action == "use":
            if use_style not in USE_FRAMES:
                raise ValueError("use_style must be one of 1, 2, 3, 4, 5, 6, 7, 11, 12, 13")
            frames["use"] = USE_FRAMES[use_style]
        if action not in frames:
            raise ValueError(f"Unknown action {action!r}; choose one of {', '.join(frames)}")
        return frames[action]

    @classmethod
    def _action_body_frame(cls, action: str, action_frame: int, use_style: int = 1) -> int:
        available = cls.action_frames(action, use_style)
        if not 0 <= action_frame < len(available):
            raise ValueError(f"{action} action frame must be from 0 to {len(available) - 1}")
        return available[action_frame]

    @staticmethod
    def _composite_arm_cells(body_frame: int) -> tuple[tuple[int, int], tuple[int, int]]:
        """Return vanilla (back, front) arm frame coordinates for a body frame."""
        front_by_body_frame = {
            0: (2, 0), 1: (3, 0), 2: (4, 0), 3: (5, 0), 4: (6, 0),
            5: (2, 1), 6: (3, 1), 7: (4, 1), 8: (4, 1), 9: (4, 1),
            10: (4, 1), 11: (3, 1), 12: (3, 1), 13: (3, 1),
            14: (5, 1), 15: (6, 1), 16: (6, 1), 17: (5, 1),
            18: (3, 1), 19: (3, 1),
        }
        front = front_by_body_frame[body_frame]
        return (front[0], front[1] + 2), front

    def texture_name(self, variant: int, piece: int) -> str:
        """PlayerDataInitializer.CopyVariant inheritance for the ten player outfits."""
        if variant not in range(10):
            raise ValueError("Player variant must be 0..9")
        base = 4 if variant in (4, 5, 6, 7, 9) else 0
        for index in dict.fromkeys((variant, base, 0)):
            name = f"Player_{index}_{piece}.png"
            if (self.player_path / name).is_file():
                return name
        raise FileNotFoundError(f"Missing player piece {piece} for variant {variant}")

    def compose(self, *, head_frame: int | None = None, body_cell: int | None = None,
                action: str = "idle", action_frame: int = 0, use_style: int = 1,
                hair: int = 1, alt_hair: bool = False,
                skin_variant: int = 0, pants_variant: int | None = None,
                shoes_variant: int | None = None, direction: int = 1,
                skin_color: tuple[int, int, int] = (255, 204, 160),
                hair_color: tuple[int, int, int] = (90, 55, 30),
                shirt_color: tuple[int, int, int] = (80, 140, 190),
                undershirt_color: tuple[int, int, int] = (145, 170, 185),
                eye_color: tuple[int, int, int] = (50, 80, 100),
                pants_color: tuple[int, int, int] = (70, 90, 150),
                shoes_color: tuple[int, int, int] = (90, 65, 45),
                armor_head: int = 0, armor_body: int = 0, armor_legs: int = 0,
                accessories: dict | None = None, auto_capes: bool = True,
                armor_dyes: dict | None = None, accessory_dyes: dict | None = None,
                aim_angle: float = 0,
                pose: dict | None = None,
                eye_frame: int | None = None) -> Image.Image:
        """Render the composite player, with independent base clothes and equipment."""
        options = locals().copy()
        options.pop('self')
        self._action_body_frame(action, action_frame, use_style)
        if pose is None: pose = shooting_pose(aim_angle) if action=='shoot' else builtin_pose(action, action_frame, direction)
        if pose is not None: pose = validate_pose(pose)
        if armor_head or armor_body or armor_legs or accessories or pose is not None:
            from equipment import compose_equipped
            options['pose'] = pose
            options['pants_variant'] = skin_variant if pants_variant is None else pants_variant
            options['shoes_variant'] = skin_variant if shoes_variant is None else shoes_variant
            return compose_equipped(self, options)
        body_frame = self._action_body_frame(action, action_frame, use_style)
        if head_frame is None:
            head_frame = body_frame
        if eye_frame is None:
            eye_frame = head_frame
        pants_variant = skin_variant if pants_variant is None else pants_variant
        shoes_variant = skin_variant if shoes_variant is None else shoes_variant
        female = skin_variant in (4, 5, 6, 7, 9)
        for variant in (skin_variant, pants_variant, shoes_variant):
            if variant not in range(10):
                raise ValueError("Player variant must be 0..9")
        (back_x, back_y), (front_x, front_y) = self._composite_arm_cells(body_frame)
        canvas = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
        # Main.OffsetsPlayerHeadgear[frame].Y - 2 applies to composite body pieces.
        bob = -2 if body_frame in (7, 8, 9, 14, 15, 16) else 0
        torso_x, torso_y = int(body_frame == 5), 2 if female else 0
        if body_cell is not None:
            torso_x, torso_y = body_cell % 9, body_cell // 9
        leg_frame = body_frame if action in ("walk", "jump") else 0

        def draw(piece, tint, x=0, y=0, *, variant=skin_variant, composite=True):
            source = self._open(self.player_path / self.texture_name(variant, piece))
            # Some intentionally empty vanilla pieces have the old vertical layout.
            if source.getbbox() is None:
                return
            sprite = self._frame(source, y * 9 + x, columns=9) if composite else self._frame(source, y)
            canvas.alpha_composite(self.recolor_image(sprite, tint), (0, bob if composite else 0))

        # Long hair is behind the body; only its top 26 pixels appear in front.
        hair_prefix = "Player_HairAlt" if alt_hair else "Player_Hair"
        hair_image = self._open(self.hair_path / f"{hair_prefix}_{hair}.png")
        # Hair 165 has a 42-pixel texture, but vanilla's source rectangle is
        # still the 40-pixel bodyFrame width (with a separate draw offset).
        hair_sprite = self._frame(hair_image.crop((0, 0, 40, hair_image.height)), max(head_frame - 6, 0))
        hair_sprite = self.recolor_image(hair_sprite, hair_color)
        hair_offset = (0, -2) if hair == 164 and not alt_hair else ((-2, 0) if hair == 165 else (0, 0))
        if hair in BACK_HAIR:
            canvas.alpha_composite(hair_sprite, hair_offset)
        draw(3, skin_color, torso_x, torso_y)
        draw(10, skin_color, y=leg_frame, composite=False)
        for piece, tint in ((7, skin_color), (5, skin_color), (8, undershirt_color), (13, shirt_color)):
            draw(piece, tint, back_x, back_y)
        draw(11, pants_color, y=leg_frame, variant=pants_variant, composite=False)
        draw(12, shoes_color, y=leg_frame, variant=shoes_variant, composite=False)
        if skin_variant in (3, 7, 8):
            draw(14, shirt_color, y=leg_frame, composite=False)
        for x, y in ((1, 3 if female else 1), (torso_x, torso_y)):
            draw(4, undershirt_color, x, y)
            draw(6, shirt_color, x, y)
        draw(0, skin_color, y=head_frame, composite=False)
        draw(1, (255, 255, 255), y=eye_frame, composite=False)
        draw(2, eye_color, y=eye_frame, composite=False)
        front_hair = hair_sprite.crop((0, 0, 40, 26)) if hair in BACK_HAIR else hair_sprite
        canvas.alpha_composite(front_hair, hair_offset)
        shoulder = (0, 3 if female else 1)
        arm = (front_x, front_y)
        for x, y in ((shoulder, arm) if body_frame in (1, 2, 5) else (arm, shoulder)):
            for piece, tint in ((7, skin_color), (8, undershirt_color), (13, shirt_color), (6, shirt_color)):
                draw(piece, tint, x, y)
        if direction == -1:
            canvas = canvas.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        return canvas

    def generate_sheet(self, *, heads: Iterable[int] = range(20), **options) -> Image.Image:
        frames = [self.compose(head_frame=index, **options) for index in heads]
        if not frames:
            raise ValueError("At least one frame is required")
        width, height = frames[0].size
        sheet = Image.new("RGBA", (width, height * len(frames)), (0, 0, 0, 0))
        for index, frame in enumerate(frames):
            sheet.alpha_composite(frame, (0, index * height))
        return sheet

    def generate_action_sheet(self, *, action: str, use_style: int = 1, **options) -> Image.Image:
        frames = [self.compose(action=action, action_frame=index, use_style=use_style, **options)
                  for index in range(len(self.action_frames(action, use_style))) ]
        width, height = frames[0].size
        sheet = Image.new("RGBA", (width * len(frames), height), (0, 0, 0, 0))
        for index, frame in enumerate(frames):
            sheet.alpha_composite(frame, (index * width, 0))
        return sheet

    def Generate(self, output_path: str | Path = "output.png", **options) -> Image.Image:
        image = self.compose(**options)
        image.save(output_path)
        return image


def _color(value: str) -> tuple[int, int, int]:
    try:
        channels = tuple(int(part) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Color must be R,G,B") from error
    if len(channels) != 3 or any(channel < 0 or channel > 255 for channel in channels):
        raise argparse.ArgumentTypeError("Color must contain three values from 0 to 255")
    return channels


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose a Terraria player sprite from extracted textures.")
    parser.add_argument("--assets", type=Path, default=ROOT / "Assets", help="Asset root containing Player/ and Hair/")
    parser.add_argument("--output", type=Path, default=ROOT / "output.png")
    parser.add_argument("--head-frame", type=int, default=None, help="Override head animation frame (0-19)")
    parser.add_argument("--body-cell", type=int, default=None,
                        help="Override the 40x56 torso cell selected for the action")
    parser.add_argument("--action", choices=(*FRAMES, "use"), default="idle",
                        help="Body/arm animation to render")
    parser.add_argument("--action-frame", type=int, default=0,
                        help="Frame within the selected action (walk 0-12; use depends on style)")
    parser.add_argument("--use-style", type=int, default=1,
                        help="Terraria item use style used to select use animation frames")
    parser.add_argument("--hair", type=int, default=1, help="Vanilla hair id")
    parser.add_argument("--alt-hair", action="store_true", help="Use the Alt hair sheet")
    parser.add_argument("--armor-head", type=int, default=0, help="Head equipment texture ID (0 = none)")
    parser.add_argument("--aim-angle", type=float, default=0, help="Shooting target angle: right=0, down=90, left=180")
    parser.add_argument("--armor-body", type=int, default=0, help="Body equipment texture ID (0 = none)")
    parser.add_argument("--armor-legs", type=int, default=0, help="Leg equipment texture ID (0 = none)")
    parser.add_argument("--skin", type=_color, default=(255, 204, 160), help="Skin tint as R,G,B")
    parser.add_argument("--hair-color", type=_color, default=(90, 55, 30), help="Hair tint as R,G,B")
    parser.add_argument("--shirt-color", type=_color, default=(80, 140, 190), help="Shirt tint as R,G,B")
    parser.add_argument("--pants-color", type=_color, default=(70, 90, 150), help="Pants tint as R,G,B")
    parser.add_argument("--shoes-color", type=_color, default=(90, 65, 45), help="Shoes tint as R,G,B")
    parser.add_argument("--sheet", action="store_true", help="Write all 20 head/eye animation frames vertically")
    parser.add_argument("--action-sheet", action="store_true",
                        help="Write the selected action's arm frames in a horizontal strip")
    args = parser.parse_args()

    generator = TerrariaCharacterGenerator(args.assets)
    options = {"body_cell": args.body_cell, "action": args.action,
               "action_frame": args.action_frame, "use_style": args.use_style, "hair": args.hair,
               "alt_hair": args.alt_hair, "skin_color": args.skin,
               "hair_color": args.hair_color, "shirt_color": args.shirt_color,
               "pants_color": args.pants_color, "shoes_color": args.shoes_color,
               "armor_head": args.armor_head, "armor_body": args.armor_body, "armor_legs": args.armor_legs,
               "aim_angle": args.aim_angle}
    if args.action_sheet:
        action_options = {key: value for key, value in options.items()
                          if key not in ("action", "action_frame")}
        image = generator.generate_action_sheet(action=args.action, **action_options)
    elif args.sheet:
        image = generator.generate_sheet(**options)
    else:
        image = generator.compose(head_frame=args.head_frame, **options)
    image.save(args.output)
    print(f"Saved {image.width}x{image.height} sprite to {args.output.resolve()}")


if __name__ == "__main__":
    main()
