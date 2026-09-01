# Crop browser screenshot (1280x720) to OG cover 1200x630
import zlib, struct, sys

src = sys.argv[1]
dst = sys.argv[2]

data = open(src, 'rb').read()
pos = 8
idat = b''
while pos < len(data):
    length = struct.unpack('>I', data[pos:pos+4])[0]
    ctype = data[pos+4:pos+8]
    if ctype == b'IHDR':
        W, H, bitd, ctyp, comp, filt, inter = struct.unpack('>IIBBBBB', data[pos+8:pos+8+13])
    elif ctype == b'IDAT':
        idat += data[pos+8:pos+8+length]
    pos += 12 + length

raw = zlib.decompress(idat)
stride = W * 3
img = bytearray(W * H * 3)
prev = bytearray(stride)
p = 0
for y in range(H):
    ftype = raw[p]; p += 1
    line = bytearray(raw[p:p+stride]); p += stride
    if ftype == 1:
        for i in range(3, stride): line[i] = (line[i] + line[i-3]) & 0xff
    elif ftype == 2:
        for i in range(stride): line[i] = (line[i] + prev[i]) & 0xff
    elif ftype == 3:
        for i in range(stride):
            a = line[i-3] if i >= 3 else 0
            line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xff
    elif ftype == 4:
        for i in range(stride):
            a = line[i-3] if i >= 3 else 0
            b_ = prev[i]
            c_ = prev[i-3] if i >= 3 else 0
            pp = a + b_ - c_
            pa, pb, pc = abs(pp-a), abs(pp-b_), abs(pp-c_)
            pr = a if (pa <= pb and pa <= pc) else (b_ if pb <= pc else c_)
            line[i] = (line[i] + pr) & 0xff
    img[y*stride:(y+1)*stride] = line
    prev = line

def is_dark(px):
    r, g, b = px
    return r < 45 and g < 50 and b < 60

x0, x1, y0, y1 = W, 0, H, 0
for y in range(0, H, 2):
    for x in range(0, W, 2):
        i = (y*W + x) * 3
        if is_dark((img[i], img[i+1], img[i+2])):
            x0 = min(x0, x); x1 = max(x1, x)
            y0 = min(y0, y); y1 = max(y1, y)

crop_w, crop_h = 1200, 630
ox = max(0, min(W - crop_w, (x0 + x1)//2 - crop_w//2))
oy = max(0, min(H - crop_h, (y0 + y1)//2 - crop_h//2))

out = bytearray()
for y in range(oy, oy + crop_h):
    base = y * stride + ox * 3
    out += img[base:base + crop_w*3]

def chunk(ctype, cdata):
    c = ctype + cdata
    return struct.pack('>I', len(cdata)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', crop_w, crop_h, 8, 2, 0, 0, 0))
raw_out = b''
step = crop_w * 3
for y in range(crop_h):
    raw_out += b'\x00' + bytes(out[y*step:(y+1)*step])
png += chunk(b'IDAT', zlib.compress(raw_out, 9))
png += chunk(b'IEND', b'')
open(dst, 'wb').write(png)
print(dst, 'written', crop_w, 'x', crop_h)
