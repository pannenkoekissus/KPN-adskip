import zipfile
import io
import re

def inspect_pigeon_methods():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for dex_name in ['classes.dex', 'classes3.dex']:
            data = bz.read(dex_name)
            # Find all strings starting with dev.flutter.pigeon or plugins.flutter.dev
            pigeon_strings = set(re.findall(rb'dev\.flutter\.pigeon\.[a-zA-Z0-9_\.]+', data))
            flutter_strings = set(re.findall(rb'plugins\.flutter\.dev\.[a-zA-Z0-9_\.]+', data))
            
            print(f"=== {dex_name} ===")
            if pigeon_strings:
                print("Pigeon strings:")
                for s in sorted(pigeon_strings):
                    print(" ", s.decode())
            if flutter_strings:
                print("Flutter strings:")
                for s in sorted(flutter_strings):
                    print(" ", s.decode())

if __name__ == '__main__':
    inspect_pigeon_methods()
