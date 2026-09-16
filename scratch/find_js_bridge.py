import zipfile
import io
import re

def find_js_bridge():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        arm64_bytes = z.read('split_config.arm64_v8a.apk')

    with zipfile.ZipFile(io.BytesIO(arm64_bytes)) as bz:
        libapp = bz.read('lib/arm64-v8a/libapp.so')

    for term in [b'_generateJavaScriptBridgeScript', b'JavaScriptBridge']:
        for m in re.finditer(term, libapp):
            start = max(0, m.start() - 500)
            end = min(len(libapp), m.end() + 500)
            chunk = libapp[start:end]
            # print printable strings
            strings = re.findall(rb'[\x20-\x7e]{4,}', chunk)
            print("Found bridge:")
            for s in strings:
                print("  ", s.decode(errors='ignore'))
            print("="*60)

if __name__ == '__main__':
    find_js_bridge()
