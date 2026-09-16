import zipfile
import io
import re

def inspect_dex():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for dex_name in ['classes.dex', 'classes3.dex']:
            data = bz.read(dex_name)
            # Find class definitions or strings (Lcom/...;)
            classes = set(re.findall(rb'L([a-zA-Z0-9_/]+);', data))
            player_classes = [c.decode(errors='ignore') for c in classes if any(k in c.lower() for k in [b'player', b'video', b'emp', b'enigma', b'media', b'kpn', b'redbee'])]
            print(f"=== {dex_name}: Found {len(classes)} class refs, {len(player_classes)} player/media related ===")
            for c in sorted(player_classes)[:40]:
                print(f"  {c}")

            # Also inspect strings near adbreak, cuepoint, restriction
            print(f"--- Context for adbreak in {dex_name} ---")
            for m in re.finditer(rb'([^\x00-\x1f\x7f-\xff]{4,80}adbreak[^\x00-\x1f\x7f-\xff]{0,80})', data, re.IGNORECASE):
                print("  STRING:", m.group(0).decode(errors='ignore'))

            print(f"--- Context for restriction in {dex_name} ---")
            for m in re.finditer(rb'([^\x00-\x1f\x7f-\xff]{4,80}restriction[^\x00-\x1f\x7f-\xff]{0,80})', data, re.IGNORECASE):
                print("  STRING:", m.group(0).decode(errors='ignore'))

if __name__ == '__main__':
    inspect_dex()
