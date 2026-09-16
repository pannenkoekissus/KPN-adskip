import zipfile
import io
import re

def search_strings():
    # Check split_config.arm64_v8a.apk
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        print("Files in arm64 apk:", bz.namelist())
        libapp = bz.read('lib/arm64-v8a/libapp.so')
        print(f"libapp.so size: {len(libapp)} bytes")

        # Search for tv.kpn.com or shaka or emp or video player keywords in libapp.so
        for term in [b'tv.kpn.com', b'kpn.com', b'InAppWebView', b'shaka', b'empclient', b'adbreak', b'trickplay', b'currentTime', b'seek']:
            matches = list(re.finditer(term, libapp, re.IGNORECASE))
            print(f"Term '{term.decode()}': {len(matches)} occurrences")
            for m in matches[:5]:
                start = max(0, m.start() - 40)
                end = min(len(libapp), m.end() + 40)
                snippet = libapp[start:end]
                # print printable chars
                clean = "".join([chr(b) if 32 <= b < 127 else "." for b in snippet])
                print(f"   [{clean}]")

if __name__ == '__main__':
    search_strings()
