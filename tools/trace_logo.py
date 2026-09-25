"""Trace the logo images in brand/ into the SVGs and icons the site uses.

Run by hand when the logo changes. build_site.py only copies what this writes,
so the build needs no imaging libraries, and the deploy runner has none.

  brand/logo-wide.jpeg     -> brand/logo-wide.svg      the header
  brand/logo-stacked.jpeg  -> brand/logo-stacked.svg   the home page
                           -> brand/mark.svg           the drawing alone
                           -> brand/favicon.ico, brand/apple-touch-icon.png

The SVGs carry no colour; build_site.py adds it, light and dark, as it copies
them. Needs Pillow, numpy, opencv-python and potracer (pip install potracer).
"""
import pathlib
import numpy as np
import cv2
import potrace
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
SCALE = 4                 # trace at 4x: a threshold taken after upscaling gives smooth edges
TOL = .35                 # potrace's curve-merging tolerance, in source pixels
PAPER = (251, 249, 244)   # --bg, for the drawing on the icons' green tile
INK = (24, 64, 40)        # the logo's green, sampled from the images
# In the wide image the drawing stands 1.67 times the height of the two lines
# of words beside it. At header height that left "What's in a Word?" about
# 13px tall, so the header version draws it at this multiple of the words
# instead (1.2 and 1.4 were tried; at 1.0 the quill's tip meets the top of the
# W). The words themselves are untouched.
MARK_TO_WORDS = 1.0
GAP = 16                  # between the drawing and the words, in source pixels (12 in the image)


def coverage(path):
    """0..1 ink coverage per pixel: 0 on the paper, 1 on the solid green."""
    g = np.asarray(Image.open(path).convert("L")).astype(np.float32)
    paper, ink = np.percentile(g, 90), np.percentile(g[g < 120], 5)
    cov = np.clip((paper - g) / (paper - ink), 0, 1)
    # The images carry faint specks of dust well away from the drawing. Keep only
    # the parts that reach solid ink somewhere; a speck never does.
    n, lab, stats, _ = cv2.connectedComponentsWithStats((cov > .35).astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        keep[i] = cov[lab == i].max() > .8 and stats[i, cv2.CC_STAT_AREA] >= 12
    cov[~keep[lab]] = 0
    return cov


def bands(mask, axis, gap):
    """Runs of rows (axis=1) or columns (axis=0) holding ink, split at gaps."""
    idx = np.where(mask.any(axis=axis))[0]
    out, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i > p + gap:
            out.append((int(s), int(p) + 1))
            s = i
        p = i
    out.append((int(s), int(p) + 1))
    return out


def bbox(cov, x0=0, y0=0, x1=None, y1=None):
    ys, xs = np.where(cov[y0:y1, x0:x1] > .35)
    return (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1)


def trace(cov, box, pad=3):
    """potrace the region box = (x0, y0, x1, y1). Returns its outlines in the
    image's own pixel coordinates, as [(start, [segment, ...]), ...] where a
    segment is ("L", point) or ("C", c1, c2, end)."""
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    big = cv2.resize(cov[y0:y1, x0:x1], None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), SCALE * .35)
    # potracer takes dark pixels as the shape, so the ink goes in as False (0).
    # The tolerance is in traced pixels, so it scales with SCALE.
    path = potrace.Bitmap(big <= .5).trace(turdsize=SCALE * SCALE * 6, alphamax=1.0,
                                           opticurve=True, opttolerance=TOL * SCALE)
    pt = lambda q: (x0 + q.x / SCALE, y0 + q.y / SCALE)
    shapes = []
    for curve in path:
        segs = []
        for s in curve.segments:
            if s.is_corner:
                segs += [("L", pt(s.c)), ("L", pt(s.end_point))]
            else:
                segs.append(("C", pt(s.c1), pt(s.c2), pt(s.end_point)))
        shapes.append((pt(curve.start_point), segs))
    return shapes


def moved(shapes, k, dx, dy):
    f = lambda p: (p[0] * k + dx, p[1] * k + dy)
    return [(f(start), [(s[0], *map(f, s[1:])) for s in segs]) for start, segs in shapes]


def nums(vals):
    """Numbers as SVG path data writes them: a minus sign is its own separator."""
    out = ""
    for v in vals:
        out += (str(v) if not out or v < 0 else " " + str(v))
    return out


def path_d(shapes, ox, oy):
    """Path data in tenths of a source pixel with relative moves throughout.
    Each point is rounded before the difference is taken, so nothing drifts."""
    t = lambda p: (round((p[0] - ox) * 10), round((p[1] - oy) * 10))
    d = []
    for start, segs in shapes:
        cur = t(start)
        d.append("M" + nums(cur))
        for s in segs:
            pts = [t(p) for p in s[1:]]
            d.append(s[0].lower() + nums([v for p in pts for v in (p[0] - cur[0], p[1] - cur[1])]))
            cur = pts[-1]
        d.append("z")
    return "".join(d)


def svg(shapes, box):
    x0, y0, x1, y1 = box
    w, h = round((x1 - x0) * 10), round((y1 - y0) * 10)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w / 10:g}" height="{h / 10:g}"><path d="{path_d(shapes, x0, y0)}"/></svg>\n')


def extent(shapes):
    pts = [p for st, segs in shapes for p in [st] + [q for s in segs for q in s[1:]]]
    return (min(p[0] for p in pts) - 1, min(p[1] for p in pts) - 1,
            max(p[0] for p in pts) + 1, max(p[1] for p in pts) + 1)


def header_lockup(cov, mark_to_words=MARK_TO_WORDS):
    """The wide logo with its drawing brought down to mark_to_words times the
    height of the words, bottom-aligned as in the image and GAP to their left."""
    # The words begin at the first gap in the columns: 11px, the widest in the image
    # short of the space between the words themselves.
    tx0 = bands(cov > .35, 0, 8)[1][0]
    mbox = bbox(cov, x1=tx0 - 1)
    tbox = bbox(cov, x0=tx0)
    words = trace(cov, tbox)
    mark = trace(cov, mbox)
    k = mark_to_words * (tbox[3] - tbox[1]) / (mbox[3] - mbox[1])
    # Scale about the drawing's bottom-right corner, keeping its drop below the
    # words' last line in proportion, then stand it GAP clear of them.
    bottom = tbox[3] + (mbox[3] - tbox[3]) * k
    mark = moved(mark, k, tbox[0] - GAP - mbox[2] * k, bottom - mbox[3] * k)
    shapes = mark + words
    return shapes, extent(shapes)


def icon(cov, box, size, grow, inset, radius=0):
    """The drawing in paper on a green tile, size x size. A tile rather than
    the bare drawing because this is what Safari shows, and a dark green
    drawing on a transparent ground vanishes in a dark tab bar. `grow`
    thickens the lines (in source pixels) first, since at 16 or 32 pixels they
    would fall below one; `radius` rounds the corners, as a fraction of size."""
    x0, y0, x1, y1 = box
    c = cov[y0:y1, x0:x1]
    if grow:
        c = cv2.dilate(c, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    h, w = c.shape
    side = int(max(h, w) / (1 - 2 * inset))
    sq = np.zeros((side, side), np.float32)
    sq[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = c
    a = cv2.resize(sq, (size, size), interpolation=cv2.INTER_AREA)[..., None]
    rgba = np.zeros((size, size, 4), np.uint8)
    rgba[..., :3] = (np.array(INK) * (1 - a) + np.array(PAPER) * a).round()
    # The corners, drawn at 8x and brought down so their edge is smooth.
    big = np.zeros((size * 8, size * 8), np.uint8)
    r = int(radius * size * 8)
    cv2.rectangle(big, (r, 0), (size * 8 - 1 - r, size * 8 - 1), 255, -1)
    cv2.rectangle(big, (0, r), (size * 8 - 1, size * 8 - 1 - r), 255, -1)
    for cx in (r, size * 8 - 1 - r):
        for cy in (r, size * 8 - 1 - r):
            cv2.circle(big, (cx, cy), r, 255, -1, cv2.LINE_AA)
    rgba[..., 3] = cv2.resize(big, (size, size), interpolation=cv2.INTER_AREA)
    return Image.fromarray(rgba, "RGBA")


def main():
    wide = coverage(BRAND / "logo-wide.jpeg")
    stacked = coverage(BRAND / "logo-stacked.jpeg")

    shapes, box = header_lockup(wide)
    (BRAND / "logo-wide.svg").write_text(svg(shapes, box), encoding="utf-8")

    shapes = trace(stacked, bbox(stacked))
    (BRAND / "logo-stacked.svg").write_text(svg(shapes, extent(shapes)), encoding="utf-8")

    # The drawing is the first band of rows in the stacked image; the words follow.
    rows = bands(stacked > .35, 1, 12)
    mbox = bbox(stacked, y0=rows[0][0], y1=rows[0][1])
    shapes = trace(stacked, mbox)
    (BRAND / "mark.svg").write_text(svg(shapes, extent(shapes)), encoding="utf-8")

    small = [icon(stacked, mbox, 16, 8, .06, .19), icon(stacked, mbox, 32, 6, .1, .19),
             icon(stacked, mbox, 48, 4, .12, .19)]
    small[2].save(BRAND / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=small[:2])
    # Square: iOS rounds the corners itself.
    icon(stacked, mbox, 180, 2, .17).save(BRAND / "apple-touch-icon.png", optimize=True)

    for f in ("logo-wide.svg", "logo-stacked.svg", "mark.svg", "favicon.ico", "apple-touch-icon.png"):
        print(f"brand/{f}  {(BRAND / f).stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
