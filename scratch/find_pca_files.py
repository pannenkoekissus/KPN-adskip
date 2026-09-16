import zipfile
import io
import re

def find_pca_files():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    dart_files = set(re.findall(rb'package:pca_app/[a-zA-Z0-9_/.]+\.dart', libapp))
    print(f"Found {len(dart_files)} pca_app Dart files:")
    for f in sorted(dart_files):
        decoded = f.decode()
        if any(w in decoded for w in ['video', 'player', 'trick', 'ad', 'stream', 'media', 'seek']):
            print(" ", decoded)

if __name__ == '__main__':
    find_pca_files()
