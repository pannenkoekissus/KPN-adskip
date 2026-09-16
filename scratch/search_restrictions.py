import zipfile
import io
import re

def search_restrictions():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    keywords = [
        b'fastForward', b'fast_forward', b'canSeek', b'isSeekable',
        b'trickplay', b'trickPlay', b'adBreak', b'ad_break',
        b'block_seeking', b'disableSeek', b'seekAllowed',
        b'RTL', b'commercial', b'adSkip', b'ad_skip', b'sko'
    ]

    for kw in keywords:
        matches = list(re.finditer(kw, libapp, re.IGNORECASE))
        print(f"Keyword '{kw.decode()}': {len(matches)} matches")
        for m in matches[:8]:
            start = max(0, m.start() - 60)
            end = min(len(libapp), m.end() + 60)
            chunk = libapp[start:end]
            words = re.findall(rb'[a-zA-Z0-9_\.\-\:\/\$]{3,}', chunk)
            print("   " + " ".join([w.decode(errors='ignore') for w in words]))

if __name__ == '__main__':
    search_restrictions()
