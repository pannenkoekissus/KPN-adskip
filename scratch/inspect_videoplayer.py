import zipfile
import io
import re

def inspect_videoplayer():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for dex_name in ['classes.dex', 'classes2.dex', 'classes3.dex']:
            data = bz.read(dex_name)
            # Find classes starting with io/flutter/plugins/videoplayer or androidx/media3
            classes = set(re.findall(rb'L([a-zA-Z0-9_/]+);', data))
            matches = [c.decode(errors='ignore') for c in classes if b'videoplayer' in c.lower() or b'pigeon' in c.lower() or b'exoplayer' in c.lower()]
            if matches:
                print(f"=== {dex_name} has {len(matches)} matches ===")
                for m in sorted(matches)[:30]:
                    print(" ", m)

if __name__ == '__main__':
    inspect_videoplayer()
