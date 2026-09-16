import zipfile
import io
import re

def investigate_player():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    print("=== Searching for kpntv_trickplay context ===")
    for m in re.finditer(b'kpntv_trickplay', libapp):
        start = max(0, m.start() - 150)
        end = min(len(libapp), m.end() + 150)
        snippet = libapp[start:end]
        clean = "".join([chr(b) if 32 <= b < 127 else " " for b in snippet])
        print(clean)

    print("\n=== Searching for isTrickPlay context ===")
    for m in re.finditer(b'isTrickPlay', libapp):
        start = max(0, m.start() - 150)
        end = min(len(libapp), m.end() + 150)
        snippet = libapp[start:end]
        clean = "".join([chr(b) if 32 <= b < 127 else " " for b in snippet])
        print(clean)

    print("\n=== Searching for player plugins / channels ===")
    channels = set(re.findall(rb'([a-zA-Z0-9_\.\-]+/[a-zA-Z0-9_\.\-]+)', libapp))
    for c in sorted(list(channels)):
        if any(w in c.lower() for w in [b'video', b'player', b'media', b'kpn', b'trick', b'ad']):
            print("Channel/Method:", c.decode(errors='ignore'))

if __name__ == '__main__':
    investigate_player()
