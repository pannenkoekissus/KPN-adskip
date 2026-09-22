"""
Binary AXML (AndroidManifest.xml) patcher.

Pure-python reader/writer for the compiled Android XML format, used to inject
the AdSkipAccessibilityService <service> element into the ORIGINAL binary
manifest (apktool's own manifest re-encode breaks installs on this app, so we
edit the pristine bytes with surgical precision instead).

Format reference (AOSP ResourceTypes.h):
  file:  [u32 magic 0x00080003][u32 fileSize]
  then chunks: { u16 type, u16 headerSize (packed as u32: headerSize<<16|type),
                 u32 chunkSize, ... }
    string pool  0x0001   headerSize 0x1C
    resource map 0x0180   headerSize 0x08
    start ns     0x0100   headerSize 0x10
    end ns       0x0101   headerSize 0x10
    start element 0x0102  headerSize 0x10
    end element   0x0103  headerSize 0x10
    cdata         0x0104
    last/eof      0x0105  headerSize 0x10

String pool internals (offsets relative to pool chunk start):
  stringCount u32, styleCount u32, flags u32, stringsStart u32, stylesStart u32
  then stringOffsets[stringCount] (relative to stringsStart!)
  then styleOffsets[styleCount]
  then string data:
     utf8 (flag & 0x100): [len1][len2][bytes]  with 0x80-bit length encodings
     utf16:               [u16 len][u16 units]
  then style data.

Start element (node = header(8) + lineNumber(4) + comment(4) = 16 bytes):
  attrExt at node+16: { ns u32, name u32, attributeStart u16, attributeSize u16,
             attributeCount u16, idIndex u16, classIndex u16, styleIndex u16 }
  then attrCount attributes (20 bytes each, at attrExt+attributeStart).
  attribute: { ns u32, name u32, rawValue u32,
               typedValue{ size u16, res0 u8, dataType u8, data u32 } }
End element:  node(16) + { ns u32, name u32 } (8) = 24 bytes total.
Resource map (0x0180): u32 per string-pool index -> framework attr resource id;
  PackageParser matches manifest attributes by that id, so any attribute name we
  append to the pool must also get a map entry or its value is ignored.
"""

import struct

TYPE_STRING_POOL = 0x0001
TYPE_RES_MAP = 0x0180
TYPE_START_NS = 0x0100
TYPE_END_NS = 0x0101
TYPE_START_TAG = 0x0102
TYPE_END_TAG = 0x0103
TYPE_EOF = 0x0105

ATTR_TYPE_STRING = 0x03
ATTR_TYPE_INT_BOOLEAN = 0x12

ANDROID_NS = "http://schemas.android.com/apk/res/android"


def _parse_len8(buf, p):
    """Read an Android utf-8 string length prefix. Returns (length, newpos)."""
    b = buf[p]
    if b & 0x80:
        length = ((b & 0x7F) << 8) | buf[p + 1]
        return length, p + 2
    return b, p + 1


def _enc_len8(length):
    """Encode a UTF-8 string length the minimal way aapt/aapt2 do: one byte for
    lengths < 0x80, otherwise a two-byte form."""
    if length < 0x80:
        return bytes([length])
    return bytes([0x80 | ((length >> 8) & 0x7F), length & 0xFF])


def parse_string_pool(buf, off):
    """Return dict with pool internals + decoded strings list + chunk size."""
    word, size = struct.unpack_from("<II", buf, off)
    typ, hsize = word & 0xFFFF, word >> 16
    assert typ == TYPE_STRING_POOL, f"not a string pool at {off:#x}"
    ncount, scount, flags, sstart, srend = struct.unpack_from("<IIIII", buf, off + 8)
    utf8 = bool(flags & 0x100)
    str_offsets = struct.unpack_from(f"<{ncount}I", buf, off + 28) if ncount else ()
    base = off + sstart
    strings = []
    for o in str_offsets:
        p = base + o
        if utf8:
            clen, p = _parse_len8(buf, p)
            blen, p = _parse_len8(buf, p)
            s = buf[p:p + blen].decode("utf-8", "replace")
        else:
            ulen = struct.unpack_from("<H", buf, p)[0]
            p += 2
            s = buf[p:p + ulen * 2].decode("utf-16-le", "replace")
        strings.append(s)
    return {
        "off": off, "size": size, "hsize": hsize,
        "ncount": ncount, "scount": scount, "flags": flags,
        "stringsStart": sstart, "stylesStart": srend,
        "strings": strings, "utf8": utf8,
    }


def _pool_chunk_bytes(pool):
    """Rebuild a string-pool chunk with appended strings, preserving indices."""
    n = len(pool["strings"])
    s = pool["scount"]
    hdr = 28  # 8 chunk hdr + 20 pool header
    strings_start = hdr + 4 * n + 4 * s
    # Stored offsets are BYTE offsets, always: AOSP ResStringPool::stringAt does
    #   const uint32_t off = mEntries[idx] / (isUTF8 ? 1 : 2);
    # i.e. it divides a stored byte offset to get the unit16_t index. So ANY
    # pool that could install cleanly stores byte offsets; unit=2 would silently
    # halve our new strings' offsets on device. Unit is hardcoded to 1.
    unit = 1
    # body starts with the ORIGINAL string-data region byte-for-byte (all pre-
    # existing strings live there, and their offsets are relative to
    # stringsStart, so they stay valid as long as that region is contiguous from
    # the start of the new data area). New strings append after it.
    body = bytearray(pool["data_slice"])
    offsets = []
    old_offsets = pool.get("old_offsets", [])
    for i, st in enumerate(pool["strings"]):
        if i < len(old_offsets):
            # existing string bytes are already in body, in place
            offsets.append(old_offsets[i])
            continue
        # aapt aligns pool string entries to 4 bytes
        while len(body) % 4:
            body.append(0)
        offsets.append(len(body) // unit)
        if pool["utf8"]:
            enc = st.encode("utf-8")
            body += _enc_len8(len(st)) + _enc_len8(len(enc)) + enc
        else:
            # official UTF-16 pool format: [len u16][body][0x0000 terminator]
            body += struct.pack("<H", len(st)) + st.encode("utf-16-le") + b"\x00\x00"
    # Trailing pad to 4 bytes: ResXMLTree::setTo -> validate_chunk() rejects any
    # chunk whose (headerSize|size) is not 4-aligned, which makes the framework
    # throw "Corrupt XML binary file". The final string need not be followed by
    # anything, but chunk size and file size must be multiples of 4.
    while len(body) % 4:
        body.append(0)
    # styles: copy old raw bytes if any (we never add styles)
    pool_data = struct.pack("<IIIII", n, s, pool["flags"], strings_start, strings_start + len(body))
    out = bytearray()
    # chunk header
    out += struct.pack("<II", (0x1C << 16) | TYPE_STRING_POOL, 0)
    out += pool_data
    for o in offsets:
        out += struct.pack("<I", o)
    for _ in range(s):
        out += struct.pack("<I", 0)
    out += body
    # styles data (should be none; if present, keep chunk consistent — not handled)
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out)


def read_file(data):
    """Parse file into (magic, size) + chunk list [(type, hsize, size, offset)]."""
    assert struct.unpack_from("<I", data, 0)[0] == 0x00080003, "not a binary AXML file"
    file_size = struct.unpack_from("<I", data, 4)[0]
    chunks = []
    off = 8
    while off < file_size:
        word, csize = struct.unpack_from("<II", data, off)
        typ, hsize = word & 0xFFFF, word >> 16
        if csize <= 0:
            break
        chunks.append((typ, hsize, csize, off))
        off += csize
    return chunks


def add_accessibility_service(data):
    """Inject the accessibility <service> into <application>. Returns bytes."""
    chunks = read_file(data)
    # --- first chunk must be the string pool ---
    ptyp, phs, psize, poff = chunks[0]
    assert ptyp == TYPE_STRING_POOL
    pool = parse_string_pool(data, poff)

    # location helpers
    def idx_of(s):
        try:
            return pool["strings"].index(s)
        except ValueError:
            return None

    def get_android_ns_idx():
        for (ct, ch, cs, co) in chunks:
            if ct == TYPE_START_NS:
                _line, _comment, _prefix, uri = struct.unpack_from("<IIII", data, co + 8)
                if uri < len(pool["strings"]) and pool["strings"][uri] == ANDROID_NS:
                    return uri
        return None

    # find indices of attribute/element names, appending as needed
    def ensure(s):
        i = idx_of(s)
        if i is None:
            pool["strings"].append(s)
            i = len(pool["strings"]) - 1
        return i

    name_id = ensure("name")
    exported_id = ensure("exported")
    permission_id = ensure("permission")
    label_id = ensure("label")
    elem_service = ensure("service")
    elem_filter = ensure("intent-filter")
    elem_action = ensure("action")
    android_ns = get_android_ns_idx()
    if android_ns is None:
        android_ns = ensure(ANDROID_NS)

    class_str = "software.morphe.kpn.AdSkipAccessibilityService"
    perm_str = "android.permission.BIND_ACCESSIBILITY_SERVICE"
    label_str = "KPN AdSkip helper"
    action_str = "android.accessibilityservice.AccessibilityService"
    v_class = ensure(class_str)
    v_perm = ensure(perm_str)
    v_label = ensure(label_str)
    v_action = ensure(action_str)

    # android attribute names our injected elements use. If the pool did not
    # already contain one of them we append it and must give it a resource-map
    # entry below, or PackageParser ignores that attribute entirely.
    FRAMEWORK_ATTR_IDS = {
        "name": 0x01010003,
        "exported": 0x01010010,
        "permission": 0x01010012,
        "label": 0x01010001,
    }
    orig_n = pool["ncount"]  # pool size before we appended anything

    # find the <application> start-tag chunk offset. The element name lives in
    # the attrExt: node = header(8)+line(4)+comment(4) = 16 bytes, then
    # { ns u32, name u32, ... } -> name at co+20.
    app_off = None
    for (ct, ch, cs, co) in chunks:
        if ct == TYPE_START_TAG:
            _ns, name = struct.unpack_from("<II", data, co + 16)
            if name == idx_of("application"):
                app_off = co
                break
    if app_off is None:
        raise SystemExit("Manifest: <application> start tag not found")

    # build attribute typed-value helper
    def attr(ns, nm, dtype, dval):
        tv = struct.pack("<HBB", 8, 0, dtype) + struct.pack("<I", dval)
        # rawValue = the string-pool index for string attrs (matches aapt),
        # 0xFFFFFFFF ("no raw value") for everything else.
        raw = dval if dtype == ATTR_TYPE_STRING else 0xFFFFFFFF
        return struct.pack("<III", ns, nm, raw) + tv

    def start_tag(elem_name_idx, attrs):
        # node frame: header(8) + lineNumber(4) + comment(4) = 16 bytes, then
        # the attrExt { ns u32, name u32, attributeStart u16, attributeSize u16,
        # attributeCount u16, idIndex u16, classIndex u16, styleIndex u16 },
        # then the attributes themselves. attributeStart is relative to the
        # attrExt start, hence 0x14 (= 20 bytes of attrExt). Element ns is
        # 0xFFFFFFFF ("no namespace") exactly like aapt writes it.
        body = (
            struct.pack("<II", 0, 0xFFFFFFFF)  # lineNumber, comment (-1 = none)
            + struct.pack("<IIHHHHHH", 0xFFFFFFFF, elem_name_idx, 0x14, 0x14, len(attrs), 0, 0, 0)
            + b"".join(attrs)
        )
        size = 8 + len(body)  # chunk header + node frame + attrExt + attrs
        return struct.pack("<II", (0x10 << 16) | TYPE_START_TAG, size) + body

    def end_tag(elem_name_idx):
        # node frame (16) + endElementExt { ns u32, name u32 } (8) = 24 total.
        body = struct.pack("<IIII", 0, 0xFFFFFFFF, 0xFFFFFFFF, elem_name_idx)
        return struct.pack("<II", (0x10 << 16) | TYPE_END_TAG, 24) + body

    service_attrs = [
        attr(android_ns, name_id, ATTR_TYPE_STRING, v_class),
        attr(android_ns, exported_id, ATTR_TYPE_INT_BOOLEAN, 0),
        attr(android_ns, permission_id, ATTR_TYPE_STRING, v_perm),
        attr(android_ns, label_id, ATTR_TYPE_STRING, v_label),
    ]
    action_attrs = [attr(android_ns, name_id, ATTR_TYPE_STRING, v_action)]

    service_chunk = (
        start_tag(elem_service, service_attrs)
        + start_tag(elem_filter, [])
        + start_tag(elem_action, action_attrs)
        + end_tag(elem_action)
        + end_tag(elem_filter)
        + end_tag(elem_service)
    )

    # --- resource map (0x0180): index == string-pool index, value == framework
    # attribute resource id. PackageParser resolves manifest attributes through
    # this map, so any NEW attribute-name string needs an entry; slots for new
    # non-attribute strings stay 0. If the original file had no map chunk, we
    # emit a full one right after the string pool. ---
    map_entries = []
    had_map = False
    for (ct, ch, cs, co) in chunks:
        if ct == TYPE_RES_MAP:
            had_map = True
            n_old = (cs - 8) // 4
            map_entries = list(struct.unpack_from(f"<{n_old}I", data, co + 8))
            break
    target = len(pool["strings"])
    while len(map_entries) < target:
        map_entries.append(0)
    for s, rid in FRAMEWORK_ATTR_IDS.items():
        i = idx_of(s)
        if i is not None and i >= orig_n:
            map_entries[i] = rid
    new_map = (
        struct.pack("<II", (0x8 << 16) | TYPE_RES_MAP, 8 + 4 * len(map_entries))
        + b"".join(struct.pack("<I", e) for e in map_entries)
    )

    # --- rebuild the string pool (preserving existing indices) ---
    pool["old_offsets"] = list(struct.unpack_from(f"<{pool['ncount']}I", data, poff + 28))
    if pool["scount"]:
        # manifests virtually never use styled strings; abort loudly rather than
        # emitting a pool whose style data would be silently corrupted
        raise SystemExit(
            "Manifest string pool has styles (scount=%d) - AXML patcher "
            "does not handle styled pools" % pool["scount"]
        )
    # original string-data region (all old strings + padding), byte-for-byte.
    # Old offsets are relative to stringsStart and stay valid because this
    # region is written contiguously at the start of the new data area; only
    # the offsets array grows in front of it, which we account for via
    # strings_start in _pool_chunk_bytes.
    pool["data_slice"] = data[poff + pool["stringsStart"]: poff + pool["size"]]
    new_pool = _pool_chunk_bytes(pool)

    # --- reassemble the file ---
    out = bytearray()
    out += data[0:8]  # magic + size (patched below)
    map_pending = not had_map
    for (ct, ch, cs, co) in chunks:
        if ct == TYPE_STRING_POOL:
            out += new_pool
            if map_pending:
                out += new_map  # original had no map chunk -> add one
                map_pending = False
        elif ct == TYPE_RES_MAP:
            out += new_map
        else:
            out += data[co:co + cs]
        # the <service> element becomes a child right after <application> starts
        if co == app_off:
            out += service_chunk
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out)


def verify(data):
    """Sanity: re-parse output and check the service element exists."""
    chunks = read_file(data)
    typ, hsize, csize, off = chunks[0]
    pool = parse_string_pool(data, off)
    for (ct, ch, cs, co) in chunks:
        if ct == TYPE_START_TAG:
            _ns, name = struct.unpack_from("<II", data, co + 16)  # attrExt ns+name
            if name < len(pool["strings"]) and pool["strings"][name] == "service":
                # attrExt fields after the name: attributeStart u16 @+24,
                # attributeSize u16 @+26, attributeCount u16 @+28
                attrStart, attrSize, attrCount = struct.unpack_from("<HHH", data, co + 24)
                if attrSize != 20:
                    continue
                for i in range(attrCount):
                    aoff = co + 16 + attrStart + i * attrSize
                    ans, anm, _raw = struct.unpack_from("<III", data, aoff)
                    if anm < len(pool["strings"]) and pool["strings"][anm] == "name":
                        dtype = struct.unpack_from("<B", data, aoff + 15)[0]
                        dval = struct.unpack_from("<I", data, aoff + 16)[0]
                        if dtype == ATTR_TYPE_STRING and dval < len(pool["strings"]):
                            if pool["strings"][dval] == "software.morphe.kpn.AdSkipAccessibilityService":
                                return True
    return False


def pool_info(data):
    """Diagnostics about the (patched) manifest's string pool."""
    chunks = read_file(data)
    typ, hsize, csize, off = chunks[0]
    pool = parse_string_pool(data, off)
    return {
        "utf8": pool["utf8"],
        "ncount": pool["ncount"],
        "scount": pool["scount"],
        "flags": pool["flags"],
        "size": pool["size"],
    }


def _chunk_desc(ct):
    names = {0x0001: "string pool", 0x0180: "resource map", 0x0100: "start ns",
             0x0101: "end ns", 0x0102: "start element", 0x0103: "end element",
             0x0104: "cdata", 0x0105: "end doc"}
    return names.get(ct, "0x%04x" % ct)


def _strict_str(data, pool_off, pool, i):
    """Decode pool string i with hard bounds; None if invalid."""
    if i is None or i >= pool["ncount"]:
        return None
    o = struct.unpack_from("<I", data, pool_off + 28 + 4 * i)[0]
    base = pool_off + pool["stringsStart"]
    data_end = pool_off + pool["size"]
    p = base + o
    if p >= data_end:
        return None
    if pool["utf8"]:
        _clen, p2 = _parse_len8(data, p)
        blen, p3 = _parse_len8(data, p2)
        if p3 + blen > data_end:
            return None
        try:
            return data[p3:p3 + blen].decode("utf-8")
        except UnicodeDecodeError:
            return None
    else:
        if p + 2 > data_end:
            return None
        ulen = struct.unpack_from("<H", data, p)[0]
        p2 = p + 2
        if p2 + ulen * 2 > data_end:
            return None
        try:
            return data[p2:p2 + ulen * 2].decode("utf-16-le")
        except UnicodeDecodeError:
            return None


def validate_manifest(data, original=None):
    """Strictly validate a (patched) binary AXML file the way the framework's
    ResXMLTree/ResStringPool would parse it: magic + file size, every chunk
    header, string-pool bounds for EVERY string, a balanced element tree with
    every name/attr/index in pool range, and the resource map length.

    Raises SystemExit with a detailed report on the first structural problem."""
    problems = []

    def bad(msg):
        problems.append(msg)

    if len(data) < 8:
        bad("file too short (%d bytes)" % len(data))
        raise SystemExit("AXML validation failed:\n- " + "\n- ".join(problems))

    magic, file_size = struct.unpack_from("<II", data, 0)
    if magic != 0x00080003:
        bad("bad magic %08x (want 00080003)" % magic)
    if file_size != len(data):
        bad("declared size %d != actual size %d" % (file_size, len(data)))
    if file_size > len(data):
        bad("declared size %d exceeds available bytes %d" % (file_size, len(data)))

    chunks = read_file(data)
    pool_off = None
    map_off = None
    for (ct, hs, cs, co) in chunks:
        # Exact headerSize is only enforced for chunk types the patcher itself
        # emits (string pool, resource map, and element tags written with the
        # format's mandatory node header). Everything else -- ns chunks, cdata,
        # and the document terminator -- is byte-copied from the pristine
        # manifest, whose toolchain conventions (e.g. aapt vs aapt2 header
        # sizes) must not be second-guessed here; only sanity-check them.
        known_hsize = {0x0001: 0x1C, 0x0180: 0x08, 0x0102: 0x10, 0x0103: 0x10}
        if ct in known_hsize and hs != known_hsize[ct]:
            bad("chunk %s @%#x headerSize %#x (want %#x)"
                % (_chunk_desc(ct), co, hs, known_hsize[ct]))
        if hs < 8 or hs > cs:
            bad("chunk %s @%#x headerSize %#x > chunk size %#x"
                % (_chunk_desc(ct), co, hs, cs))
        # ResXMLTree::setTo -> validate_chunk() rejects ANY chunk whose
        # (headerSize | size) is not 4-byte aligned ("not on an integer
        # boundary"). This bites the framework as "Corrupt XML binary file".
        if ((hs | cs) & 0x3) != 0:
            bad("chunk %s @%#x headerSize %#x or size %#x is not 4-byte aligned"
                % (_chunk_desc(ct), co, hs, cs))
        if ct == 0x0180:
            map_off = co
        if ct == 0x0001 and pool_off is None:
            pool_off = co

    # A valid XML tree does not have to end in an END_DOCUMENT chunk:
    # ResXMLTree walks its chunk list and reports END_DOCUMENT once it runs
    # out. The pristine manifest in this build ends with an END_NAMESPACE
    # chunk and never contains a 0x0105 terminator, yet the platform parses
    # it fine -- so when the original is available, require the patched
    # terminator to mirror the pristine tail instead of demanding end-doc.
    if original is not None:
        op_last = read_file(original)[-1][0]
        if chunks[-1][0] != op_last:
            bad("last chunk is %s, pristine manifest ends with %s"
                % (_chunk_desc(chunks[-1][0]), _chunk_desc(op_last)))
    elif chunks[-1][0] not in (0x0105, 0x0101):
        bad("last chunk is %s, expected end-document"
            % _chunk_desc(chunks[-1][0]))
    # chunk walk must cover the entire file exactly
    walked = 8 + sum(cs for (_ct, _hs, cs, _co) in chunks)
    if walked != len(data):
        bad("chunk sizes sum to %#x but file is %#x" % (walked, len(data)))

    if pool_off is None:
        bad("no string pool chunk")
    else:
        pool = parse_string_pool(data, pool_off)
        if pool["scount"]:
            bad("pool has %d styles (unsupported)" % pool["scount"])
        ncount = pool["ncount"]
        stack = []
        for (ct, hs, cs, co) in chunks:
            if ct == 0x0102:
                _ns, name = struct.unpack_from("<II", data, co + 16)
                if _strict_str(data, pool_off, pool, name) is None:
                    bad("start element @%#x has invalid name index %d" % (co, name))
                attrStart, attrSize, attrCount = struct.unpack_from("<HHH", data, co + 24)
                if attrSize != 0x14:
                    bad("start element @%#x attributeSize %d (want 20)" % (co, attrSize))
                for i in range(attrCount):
                    aoff = co + 16 + attrStart + i * attrSize
                    ans, anm, _raw = struct.unpack_from("<III", data, aoff)
                    # Name-only attributes (e.g. the root's `package`, and in
                    # some aapt2 manifests the version attrs) carry ns ==
                    # 0xFFFFFFFF, aapt's "no namespace" sentinel. AOSP's
                    # ResXMLTree::getAttributeNamespace special-cases that
                    # value and returns the empty string instead of a pool
                    # lookup, so it must not be flagged as out of range.
                    if ans != 0xFFFFFFFF and _strict_str(data, pool_off, pool, ans) is None:
                        bad("element @%#x attr%d ns index %d out of range" % (co, i, ans))
                    if _strict_str(data, pool_off, pool, anm) is None:
                        bad("element @%#x attr%d name index %d out of range" % (co, i, anm))
                    dtype = data[aoff + 15]
                    dval = struct.unpack_from("<I", data, aoff + 16)[0]
                    if dtype == 0x03 and _strict_str(data, pool_off, pool, dval) is None:
                        bad("element @%#x attr%d string value index %d out of range" % (co, i, dval))
                stack.append(name)
            elif ct == 0x0103:
                _ens, name = struct.unpack_from("<II", data, co + 16)
                if not stack:
                    bad("END element @%#x with empty stack" % co)
                elif stack[-1] != name:
                    bad("END element @%#x name %d != open element %d" % (co, name, stack[-1]))
                else:
                    stack.pop()
        if stack:
            bad("unclosed element(s): %d still open" % len(stack))

        if map_off is not None:
            n_entries = (struct.unpack_from("<I", data, map_off + 4)[0] - 8) // 4
            if n_entries != ncount:
                bad("resource map has %d entries but pool has %d strings"
                    % (n_entries, ncount))

        if original is not None:
            ochunks = read_file(original)
            opool_off = next(co for (ct, _h, _s, co) in ochunks if ct == 0x0001)
            opool = parse_string_pool(original, opool_off)
            for k in range(opool["ncount"]):
                got = _strict_str(data, pool_off, pool, k)
                want = _strict_str(original, opool_off, opool, k)
                if got != want:
                    bad("string[%d] changed after patch:\n  before=%r\n  after =%r"
                        % (k, want, got))

    if problems:
        raise SystemExit("AXML validation failed:\n- " + "\n- ".join(problems))
    return True