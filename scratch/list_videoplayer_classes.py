import zipfile
import io
import re

def list_videoplayer_classes():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for dex_name in ['classes.dex', 'classes2.dex', 'classes3.dex']:
            data = bz.read(dex_name)
            classes = set(re.findall(rb'L([a-zA-Z0-9_/$]+);', data))
            matches = [c.decode(errors='ignore') for c in classes if b'videoplayer' in c.lower()]
            if matches:
                print(f"=== {dex_name} ===")
                for m in sorted(matches):
                    print(" ", m)

if __name__ == '__main__':
    list_videoplayer_classes()
