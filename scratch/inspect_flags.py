import zipfile
import io
import re

def inspect_flags():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    targets = [b'isFastForwardBlocked', b'canSeek', b'isTrickPlay', b'talpa_ad_skip']
    for t in targets:
        for m in re.finditer(t, libapp):
            start = max(0, m.start() - 300)
            end = min(len(libapp), m.end() + 300)
            chunk = libapp[start:end]
            words = re.findall(rb'[a-zA-Z0-9_\.\-\:\/\$]{3,}', chunk)
            print(f"=== Target: {t.decode()} ===")
            print(" ".join([w.decode(errors='ignore') for w in words]))

if __name__ == '__main__':
    inspect_flags()
