"""Number check (phase 18): every price, quantity or total in the assistant's answer must have
come out of a tool in the same conversation. Small numbers (below 10, e.g. "3 أيام") and
years/dates are not checked."""

import json
import re

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:[,،]\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")


def numbers_in_text(text: str) -> set[float]:
	text = (text or "").translate(ARABIC_DIGITS)
	out = set()
	for m in NUMBER.findall(text):
		try:
			out.add(round(abs(float(m.replace(",", "").replace("،", ""))), 2))
		except ValueError:
			continue
	return out


def numbers_in_outputs(outputs: list) -> set[float]:
	return numbers_in_text(json.dumps(outputs, ensure_ascii=False, default=str))


def unsupported_numbers(answer: str, tool_outputs: list) -> list[float]:
	known = numbers_in_outputs(tool_outputs)
	flagged = []
	for n in sorted(numbers_in_text(answer)):
		if n < 10 or (1900 <= n <= 2100 and n == int(n)):
			continue
		if n not in known:
			flagged.append(n)
	return flagged
