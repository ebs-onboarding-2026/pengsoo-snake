"""Turn the opaque-gray-background Pengsoo JPG into a trimmed transparent PNG sprite.

Border-connected flood fill only, so gray pixels *inside* the character
(eye outlines, pupils, mouth) are preserved.
"""
import sys
from collections import deque
from PIL import Image, ImageFilter

SRC = sys.argv[1]
DST = sys.argv[2]
TOL = 46          # per-channel tolerance against the seed background colour
MAX_SIDE = 160    # final sprite longest edge (renders at <=86px: DPR2 x 1.8 cells)

im = Image.open(SRC).convert("RGB")
w, h = im.size
px = im.load()

# Seed colour: average of the four corners.
corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
bg = tuple(sum(c[i] for c in corners) // len(corners) for i in range(3))


def is_bg(c):
    return all(abs(c[i] - bg[i]) <= TOL for i in range(3))


# Flood fill inward from every border pixel.
mask = bytearray(w * h)          # 1 = background
q = deque()
for x in range(w):
    for y in (0, h - 1):
        if not mask[y * w + x] and is_bg(px[x, y]):
            mask[y * w + x] = 1
            q.append((x, y))
for y in range(h):
    for x in (0, w - 1):
        if not mask[y * w + x] and is_bg(px[x, y]):
            mask[y * w + x] = 1
            q.append((x, y))

while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            i = ny * w + nx
            if not mask[i] and is_bg(px[nx, ny]):
                mask[i] = 1
                q.append((nx, ny))

removed = sum(mask)
print(f"bg seed={bg} removed={removed}px ({removed / (w * h):.1%})")

# Build the alpha channel, then blur it a touch to soften JPEG-fringed edges.
alpha = Image.frombytes("L", (w, h), bytes(0 if m else 255 for m in mask))
alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))

out = im.convert("RGBA")
out.putalpha(alpha)

bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
print("bbox", bbox)
out = out.crop(bbox)

scale = MAX_SIDE / max(out.size)
if scale < 1:
    out = out.resize(
        (round(out.width * scale), round(out.height * scale)), Image.LANCZOS
    )

out.save(DST, optimize=True)
print("saved", DST, out.size)
