"""Writes 10 JPEG photos of 4 MB or more, each with GPS EXIF, for the upload test."""

import io
import os
import sys

from PIL import Image

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
for i in range(10):
	img = Image.frombytes("RGB", (2600, 1950), os.urandom(2600 * 1950 * 3))
	exif = Image.Exif()
	exif[0x010F] = "TestCam"
	gps = exif.get_ifd(0x8825)
	gps[1], gps[2], gps[3], gps[4] = "N", (30.0, 2.0, 0.0), "E", (31.0, 14.0, 0.0)
	buf = io.BytesIO()
	img.save(buf, format="JPEG", quality=97, exif=exif)
	assert buf.tell() >= 4 * 1024 * 1024, buf.tell()
	with open(os.path.join(out_dir, f"site-{i + 1}.jpg"), "wb") as f:
		f.write(buf.getvalue())

# Phase 14: a floor plan PDF, 800 × 600 pt, 1 pt = 1 px at scale 1.
# Calibration wall: (100, 500) → (350, 500) = 250 px = 5 m. Room: (100, 100)–(300, 350) = 4 × 5 m.
if len(sys.argv) > 2:
	from PIL import ImageDraw

	plan = Image.new("RGB", (800, 600), "white")
	d = ImageDraw.Draw(plan)
	d.rectangle((100, 100, 300, 350), outline="black", width=3)
	d.line((100, 500, 350, 500), fill="black", width=3)
	plan.save(sys.argv[2], "PDF", resolution=72)
print("ok")
