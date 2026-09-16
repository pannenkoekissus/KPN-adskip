import zipfile
import io
import re

def inspect_kpn_classes():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for dex_name in ['classes.dex', 'classes2.dex', 'classes3.dex']:
            data = bz.read(dex_name)
            classes = set(re.findall(rb'Lcom/kpn/[a-zA-Z0-9_/$]+;', data))
            if classes:
                print(f"=== {dex_name} has {len(classes)} KPN classes ===")
                for c in sorted(classes):
                    print(" ", c.decode())

if __name__ == '__main__':
    inspect_kpn_classes()
