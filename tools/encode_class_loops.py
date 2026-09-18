#!/usr/bin/env python3
"""Turn captured idle frames into small looping videos for the class columns.

Input:  <capture>/<Class>/f_000.png ... + timing.json  (from Scripts/editor/capture_class_idle.py)
Output: assets/video/<class>.webm, <class>.mp4, <class>.jpg (poster / reduced-motion still)

Steps per class:
  1. Find the best loop: for each candidate period >= min_loop seconds, compare frame k with
     frame k+period (mean abs diff over a downscaled grey copy) and pick the (start, period)
     with the smallest seam. Idles are authored to loop, so a near-zero seam exists.
  2. Crop to the character's bounding box (+margin) so the video isn't mostly black.
  3. Encode. With a_NNN.exr alpha mattes present (capture run with alpha=True): VP9 webm with
     alpha + HEVC-with-alpha mp4 + PNG poster, all truly transparent. Without: opaque VP9/H.264
     on black, which the site screen-blends away.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

CAPTURE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/fr_class_capture"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "video")
CLASSES = ["Sentinel", "Hexblade", "Ironsworn", "Sage"]
MIN_LOOP = 2.0     # seconds
MARGIN = 24        # px around the union bounding box
THRESH = 12        # luminance above which a pixel counts as "character"


def load_frames(d):
    files = sorted(f for f in os.listdir(d) if f.startswith("f_") and f.endswith(".png"))
    return [Image.open(os.path.join(d, f)).convert("RGB") for f in files]


def best_loop(frames, fps):
    small = [np.asarray(f.resize((72, 101)).convert("L"), dtype=np.float32) for f in frames]
    n = len(small)
    min_p = int(MIN_LOOP * fps)
    best = (1e9, 0, n)
    for p in range(min_p, n - 1):
        for s in range(0, n - p):
            seam = np.abs(small[s] - small[s + p]).mean()
            if seam < best[0]:
                best = (seam, s, p)
    return best


def bbox(frames):
    acc = None
    for f in frames:
        a = np.asarray(f.convert("L"))
        acc = (a > THRESH) if acc is None else (acc | (a > THRESH))
    ys, xs = np.where(acc)
    w, h = frames[0].size
    x0, x1 = max(xs.min() - MARGIN, 0), min(xs.max() + MARGIN, w)
    y0, y1 = max(ys.min() - MARGIN, 0), min(ys.max() + MARGIN, h)
    # even dimensions for the encoders
    x1 -= (x1 - x0) % 2
    y1 -= (y1 - y0) % 2
    return x0, y0, x1, y1


def encode(name, frames, fps, box, alpha_dir=None, start=0):
    """alpha_dir: capture dir holding a_NNN.exr (SceneColor HDR, A = inverse opacity). When
    present the outputs carry a real alpha channel: VP9 webm (Chrome/Firefox/Edge) and HEVC mp4
    with alpha via VideoToolbox (Safari), plus a PNG poster. Without it: opaque-on-black as before."""
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join("/tmp", "fr_loop_" + name)
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        p = os.path.join(tmp, f)
        if os.path.isfile(p):        # the alpha/ subdir lives here too; it cleans itself below
            os.remove(p)
    for i, fr in enumerate(frames):
        fr.crop(box).save(os.path.join(tmp, "l_%03d.png" % i))
    seq = os.path.join(tmp, "l_%03d.png")
    x0, y0, x1, y1 = box
    crop = "crop=%d:%d:%d:%d" % (x1 - x0, y1 - y0, x0, y0)
    low = name.lower()
    if alpha_dir:
        # Alpha matte: EXR alpha is inverse opacity, so negate it, then merge onto the LDR color.
        #
        # The EXR alpha is extracted one frame at a time to 8-bit gray PNGs, with ffmpeg doing
        # nothing but the decode (`-pix_fmt rgba`) and PIL doing the channel work.
        #
        # Two separate ffmpeg >= 9 failures forced this, and both look like script bugs rather
        # than ffmpeg bugs, so they are worth naming:
        #   * filtering the .exr inline (`format=gbrapf32le,extractplanes=a,...`) dies with
        #     "Impossible to convert between the formats supported by the filter
        #     'auto_premultiply_dynamic' and the filter 'auto_scale'" — these EXRs decode as
        #     gbrapf16le and the auto-inserted premultiply filter cannot reach gbrapf32le.
        #   * doing the same extractplanes in its own pass **SIGSEGVs** ffmpeg outright.
        # Decoding straight to RGBA avoids every float-format negotiation and is fast enough.
        adir = os.path.join(tmp, "alpha")
        os.makedirs(adir, exist_ok=True)
        for f in os.listdir(adir):
            os.remove(os.path.join(adir, f))
        rgba = os.path.join(tmp, "_a_rgba.png")
        for i in range(len(frames)):
            src = os.path.join(alpha_dir, "a_%03d.exr" % (start + i))
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error",
                                   "-i", src, "-pix_fmt", "rgba", rgba])
            # EXR alpha here is INVERSE opacity: background 255, character 0. Invert it.
            a = Image.open(rgba).split()[-1].point(lambda v: 255 - v)
            a.crop(box).save(os.path.join(adir, "m_%03d.png" % i))
        os.remove(rgba)
        aseq = os.path.join(adir, "m_%03d.png")
        fc = "[0:v][1:v]alphamerge,format=yuva420p[v]"
        base = ["ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(fps), "-i", seq,
                "-framerate", str(fps), "-i", aseq,
                "-frames:v", str(len(frames)), "-filter_complex", fc, "-map", "[v]", "-an"]
        subprocess.check_call(base + ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34", "-row-mt", "1",
                                      "-pix_fmt", "yuva420p", os.path.join(OUT, low + ".webm")])
        subprocess.check_call(base + ["-c:v", "hevc_videotoolbox", "-alpha_quality", "0.8",
                                      "-q:v", "55", "-tag:v", "hvc1", "-pix_fmt", "bgra",
                                      "-movflags", "+faststart", os.path.join(OUT, low + ".mp4")])
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error",
                               "-i", os.path.join(tmp, "l_000.png"),
                               "-i", os.path.join(adir, "m_000.png"),
                               "-filter_complex", fc.replace("format=yuva420p", "format=rgba"),
                               "-map", "[v]", "-frames:v", "1", os.path.join(OUT, low + ".png")])
        return
    # Opaque path: crush near-black to true black so screen-blending on the site is clean.
    lut = [0 if v < 16 else int((v - 16) * 255 / 239) for v in range(256)] * 3
    frames[0].crop(box).point(lut).save(os.path.join(OUT, low + ".jpg"), quality=82)
    base = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", seq,
            "-vf", "curves=all='0/0 0.063/0 1/1'"]
    subprocess.check_call(base + ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34", "-row-mt", "1",
                                  "-pix_fmt", "yuv420p", "-an", os.path.join(OUT, low + ".webm")])
    subprocess.check_call(base + ["-c:v", "libx264", "-crf", "26", "-preset", "slow", "-profile:v", "main",
                                  "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                                  os.path.join(OUT, low + ".mp4")])


def main():
    for name in CLASSES:
        d = os.path.join(CAPTURE, name)
        if not os.path.isdir(d):
            print("skip", name, "(no capture)")
            continue
        timing = json.load(open(os.path.join(d, "timing.json")))
        deltas = timing["deltas"]
        fps = round(1.0 / (sum(deltas) / len(deltas)))
        frames = load_frames(d)
        seam, s, p = best_loop(frames, fps)
        loop = frames[s:s + p]
        box = bbox(loop)
        has_alpha = os.path.exists(os.path.join(d, "a_000.exr"))
        encode(name, loop, fps, box, alpha_dir=d if has_alpha else None, start=s)
        print("%-9s frames=%d fps=%d loop=[%d:%d] seam=%.2f crop=%s" % (name, len(frames), fps, s, s + p, seam, box))


if __name__ == "__main__":
    main()
