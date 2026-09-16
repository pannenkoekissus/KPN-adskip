import zipfile
import io
import struct

def parse_dex_header(data):
    magic = data[:8]
    if not magic.startswith(b'dex\n'):
        return None
    string_ids_size, string_ids_off = struct.unpack_from('<II', data, 0x38)
    type_ids_size, type_ids_off = struct.unpack_from('<II', data, 0x40)
    proto_ids_size, proto_ids_off = struct.unpack_from('<II', data, 0x48)
    field_ids_size, field_ids_off = struct.unpack_from('<II', data, 0x50)
    method_ids_size, method_ids_off = struct.unpack_from('<II', data, 0x58)
    class_defs_size, class_defs_off = struct.unpack_from('<II', data, 0x60)
    return {
        'string_ids_size': string_ids_size, 'string_ids_off': string_ids_off,
        'type_ids_size': type_ids_size, 'type_ids_off': type_ids_off,
        'proto_ids_size': proto_ids_size, 'proto_ids_off': proto_ids_off,
        'field_ids_size': field_ids_size, 'field_ids_off': field_ids_off,
        'method_ids_size': method_ids_size, 'method_ids_off': method_ids_off,
        'class_defs_size': class_defs_size, 'class_defs_off': class_defs_off,
    }

def get_string(data, string_ids_off, idx):
    str_data_off = struct.unpack_from('<I', data, string_ids_off + idx * 4)[0]
    # read uleb128 length
    pos = str_data_off
    length = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        length |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
    # read c-string
    end = data.find(b'\x00', pos)
    return data[pos:end].decode('utf-8', errors='ignore')

def inspect_videoplayer_dex():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        data = bz.read('classes3.dex')

    hdr = parse_dex_header(data)
    print("DEX parsed:", hdr)

    # find all strings related to VideoPlayer
    strings = []
    for i in range(hdr['string_ids_size']):
        s = get_string(data, hdr['string_ids_off'], i)
        if 'Lio/flutter/plugins/videoplayer/VideoPlayer;' in s or 'exoPlayer' in s:
            strings.append((i, s))
    print(f"Matching strings: {len(strings)}")
    for item in strings[:10]:
        print(" ", item)

if __name__ == '__main__':
    inspect_videoplayer_dex()
