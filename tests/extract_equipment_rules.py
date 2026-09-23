"""Extract equipment names and draw sets from the user's Terraria 1.4.4 source."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--names', type=Path, help='Optional Items.json containing DisplayNames')
    args = parser.parse_args()
    source = (args.source / 'ID/ArmorIDs.cs').read_text(encoding='utf-8-sig')
    tml = (args.source / 'ID/ArmorIDs.TML.cs').read_text(encoding='utf-8-sig')
    localized = json.loads(args.names.read_text(encoding='utf-8-sig'))['DisplayNames'] if args.names else {}
    result = {'source_version':'Terraria 1.4.4 / tModLoader source', 'source_sha256':hashlib.sha256(source.encode()).hexdigest()}
    classes = list(re.finditer(r'\n\tpublic (?:partial )?class (\w+)\n', source))
    for index, match in enumerate(classes):
        slot=match[1]
        block=source[match.end():classes[index+1].start() if index+1<len(classes) else len(source)]
        extra = tml.split(f'partial class {slot}\n',1)[1].split('\n\tpartial class ',1)[0] if f'partial class {slot}\n' in tml else ''
        names = {n: name for name,n in re.findall(r'public const (?:int|sbyte|byte|short) (\w+) = (\d+);',block) if name not in ('Count','FamiliarWig','FamiliarShirt','FamiliarPants')}
        sets = {}
        for name, values in re.findall(r'bool\[\] (\w+) = Factory.CreateBoolSet\(([^)]*)\)',block+extra):
            tokens = [v.strip() for v in values.split(',') if v.strip()]
            sets[name] = {'default':bool(tokens and tokens[0]=='true'), 'exceptions':[int(v) for v in tokens if v.isdigit()]}
        mappings = {}
        for name, values in re.findall(r'int\[\] (\w+) = Factory.CreateIntSet\(-1, ([^)]*)\)',block+extra):
            numbers=[int(v) for v in values.split(',')]
            mappings[name]=dict(zip(numbers[::2],numbers[1::2]))
        result[slot.lower()] = {'names':{n:{'key':name,'label':localized.get(name,re.sub(r'(?<=[a-z])(?=[A-Z])',' ',name))} for n,name in names.items()},'sets':sets,'mappings':mappings}
    mapping = re.search(r'FrontToBackID = Factory.CreateIntSet\(-1, ([^)]*)\)',source)[1]
    ids = [int(v) for v in mapping.split(',')]
    result['head']['back_ids'] = dict(zip(ids[::2],ids[1::2]))
    output = ROOT/'equipment_rules.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Extracted draw rules and names: {output}')


if __name__ == '__main__': main()
