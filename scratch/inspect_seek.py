import zipfile
import io
import re

def inspect_channel():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        data = bz.read('classes3.dex')

    # Look for seekTo method call in VideoPlayer or AndroidVideoPlayerApi
    methods = set(re.findall(rb'seekTo[a-zA-Z0-9_$]*', data))
    print("Seek methods:", methods)

    for m in re.finditer(rb'seekTo', data):
        start = max(0, m.start() - 100)
        end = min(len(data), m.end() + 100)
        chunk = data[start:end]
        words = re.findall(rb'[a-zA-Z0-9_\.\-\:\/\$]{3,}', chunk)
        print("Context:", " ".join([w.decode(errors='ignore') for w in words]))

if __name__ == '__main__':
    inspect_channel()
