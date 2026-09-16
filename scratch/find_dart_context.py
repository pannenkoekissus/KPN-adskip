import zipfile
import io
import re

def find_context():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    for term in [b'kpntv_trickplay', b'isTrickPlay', b'video.progress.slider']:
        for m in re.finditer(term, libapp):
            start = max(0, m.start() - 250)
            end = min(len(libapp), m.end() + 250)
            chunk = libapp[start:end]
            # extract readable strings of len >= 3
            words = re.findall(rb'[a-zA-Z0-9_\.\-/\:]{3,}', chunk)
            print(f"Context for {term.decode()}:")
            print("  " + " | ".join([w.decode(errors='ignore') for w in words]))
            print("-" * 50)

if __name__ == '__main__':
    find_context()
