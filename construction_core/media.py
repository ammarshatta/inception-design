"""Server-side media handling: photo size/EXIF safety net and public copies (phase 3)."""

import io

import frappe
from PIL import Image, ImageOps

MAX_SIDE = 1600
JPEG_QUALITY = 80
MAX_PHOTO_BYTES = 500 * 1024


def _has_exif(img) -> bool:
	try:
		return bool(img.getexif())
	except Exception:
		return False


def reencode(content: bytes) -> bytes:
	"""Longest side 1600 px, JPEG quality 80, no EXIF (and so no GPS)."""
	with Image.open(io.BytesIO(content)) as img:
		img = ImageOps.exif_transpose(img)
		img.thumbnail((MAX_SIDE, MAX_SIDE))
		if img.mode not in ("RGB", "L"):
			img = img.convert("RGB")
		out = io.BytesIO()
		quality = JPEG_QUALITY
		while True:
			out.seek(0)
			out.truncate()
			img.save(out, format="JPEG", quality=quality, optimize=True)
			if out.tell() <= MAX_PHOTO_BYTES or quality <= 50:
				return out.getvalue()
			quality -= 10


def sanitize_photo(file_name: str) -> bool:
	"""Re-encode a stored photo when it is too big or still carries EXIF. Returns True if changed."""
	file = frappe.get_doc("File", file_name)
	path = file.get_full_path()
	with open(path, "rb") as f:
		content = f.read()
	try:
		with Image.open(io.BytesIO(content)) as img:
			too_big = len(content) > MAX_PHOTO_BYTES or max(img.size) > MAX_SIDE
			exif = _has_exif(img)
	except Exception:
		frappe.throw(frappe._("This file is not a photo"))
	if not too_big and not exif:
		return False
	new = reencode(content)
	with open(path, "wb") as f:
		f.write(new)
	file.db_set("file_size", len(new), update_modified=False)
	file.db_set("content_hash", frappe.utils.generate_hash(), update_modified=False)
	return True


def make_public_copy(private_url: str, update: str) -> str:
	"""A separate public file for a photo marked suitable for publishing (story P03-05)."""
	source = frappe.get_doc("File", {"file_url": private_url})
	copy = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "public-" + source.file_name,
			"content": source.get_content(),
			"is_private": 0,
			"attached_to_doctype": "Stage Update",
			"attached_to_name": update,
		}
	)
	copy.flags.public_copy = True
	copy.insert(ignore_permissions=True)
	return copy.file_url


def remove_public_copy(public_url: str) -> None:
	name = frappe.db.get_value("File", {"file_url": public_url, "is_private": 0}, "name")
	if name:
		frappe.delete_doc("File", name, ignore_permissions=True, force=True)
