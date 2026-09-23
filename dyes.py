"""Per-slot RGB multiply tint. White is an exact identity; alpha is preserved."""
import re


def validate(raw, slots):
    if not isinstance(raw, dict) or set(raw) - set(slots):
        raise ValueError('染色配置包含无效槽位')
    result = {}
    for slot, color in raw.items():
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError(f'{slot} 染色必须为 #RRGGBB')
        result[slot] = color.lower()
    return result


def rgb(color):
    return tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
