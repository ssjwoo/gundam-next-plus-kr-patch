"""Build a conservative, reproducible classification ledger for rendered GIMs.

Only explicitly reviewed images receive visual labels. Do not infer a label from
another member of the same archive or from a similar-looking filename.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RENDER = PROJECT / "analysis" / "gim_render_all_v2"
MANIFEST = RENDER / "render_manifest.json"
OUTPUT = PROJECT / "analysis" / "GIM_CLASSIFICATION_LEDGER_2026-09-24.csv"


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    images = [
        Path(item["output"]).relative_to(RENDER).as_posix()
        for record in data["records"]
        for item in record["images"]
    ]
    if len(images) != 4272 or len(set(images)) != len(images):
        raise ValueError("Unexpected render image count or duplicate paths")

    labels: dict[str, tuple[str, str]] = {}
    by_number: dict[int, str] = {}
    for image in images:
        directory = image.split("/", 1)[0]
        number = int(directory[:5])
        if number in by_number and by_number[number] != directory:
            raise ValueError(f"Ambiguous source number: {number}")
        by_number[number] = directory

    def path(number: int, picture: str) -> str:
        return f"{by_number[number]}/{picture}"

    def mark(image: str, label: str, evidence: str) -> None:
        if image not in image_set or image in labels:
            raise ValueError(f"Missing or multiply classified image: {image}")
        labels[image] = (label, evidence)

    image_set = set(images)
    for number in range(475, 485):
        if "_manual" not in by_number[number]:
            raise ValueError(f"Not a manual asset: {number}")
        mark(path(number, "part_000_picture_000.png"), "text_visual", "individual_visual_review")
    for number in range(622, 688):
        if "_inst_" not in by_number[number]:
            raise ValueError(f"Not an inst asset: {number}")
        mark(path(number, "part_000_picture_000.png"), "text_visual", "individual_visual_review")
    for number in range(764, 830):
        if "_selpi" not in by_number[number]:
            raise ValueError(f"Not a selpi asset: {number}")
        mark(path(number, "part_001_picture_000.png"), "text_visual", "individual_visual_review")
    for number in range(486, 562):
        if "_glc" not in by_number[number]:
            raise ValueError(f"Not a glc asset: {number}")
        mark(path(number, "part_001_picture_001.png"), "text_visual", "individual_visual_review")
    illust_without_visible_text = {590, 593, 599, 600, 605, 606, 609, 610}
    illust_uncertain = {604}
    for number in range(562, 622):
        if "_illust_" not in by_number[number]:
            raise ValueError(f"Not an illust asset: {number}")
        if number in illust_without_visible_text:
            label = "no_visible_text_visual"
        elif number in illust_uncertain:
            label = "text_presence_uncertain_visual"
        else:
            label = "text_visual"
        mark(path(number, "part_000_picture_000.png"), label, "individual_visual_review")

    for number, picture in [
        (470, "part_001_picture_000.png"),
        (472, "part_001_picture_000.png"),
        (472, "part_001_picture_001.png"),
        (473, "part_000_picture_000.png"),
        (474, "part_001_picture_003.png"),
        (485, "part_001_picture_001.png"),
        (485, "part_001_picture_005.png"),
        (851, "part_001_picture_000.png"),
        (851, "part_001_picture_001.png"),
        (1264, "part_001_picture_000.png"),
    ]:
        mark(path(number, picture), "text_visual", "individual_visual_review")

    for number, picture in [
        *((470, f"part_005_picture_{i:03d}.png") for i in range(4)),
        (474, "part_001_picture_004.png"),
        (474, "part_001_picture_005.png"),
        (485, "part_001_picture_002.png"),
        (485, "part_001_picture_003.png"),
        (485, "part_001_picture_004.png"),
        (698, "part_001_picture_000.png"),
        (992, "part_001_picture_000.png"),
        (1962, "part_001_picture_000.png"),
        (1887, "part_001_picture_000.png"),
    ]:
        mark(path(number, picture), "no_visible_text_visual", "individual_visual_review")

    for number, picture in [
        (470, "part_003_picture_000.png"),
        *((474, f"part_001_picture_{i:03d}.png") for i in range(3)),
        (485, "part_001_picture_000.png"),
        (485, "part_001_picture_006.png"),
        *((n, "part_001_picture_000.png") for n in (488, 496, 504)),
        (1343, "part_001_picture_000.png"),
    ]:
        mark(path(number, picture), "alpha_role_unresolved", "individual_visual_review_and_rgba_extrema")

    mark(
        path(2499, "part_000_picture_000.png"),
        "text_presence_uncertain_visual",
        "individual_visual_review",
    )

    for number, picture in [
        *((n, "part_005_picture_000.png") for n in (1828, 1830, 1834, 1837, 1838)),
        *((n, "part_003_picture_001.png") for n in (1587, 1591, 1628, 1632)),
        (1614, "part_003_picture_000.png"),
    ]:
        mark(path(number, picture), "no_visible_pixels_exact_rgba", "whole_png_rgba_extrema")

    rows = []
    for image in sorted(images):
        label, evidence = labels.get(image, ("not_reviewed", ""))
        rows.append((image, label, evidence))
    counts = Counter(row[1] for row in rows)
    expected = {
        "text_visual": 279,
        "no_visible_text_visual": 21,
        "text_presence_uncertain_visual": 2,
        "alpha_role_unresolved": 10,
        "no_visible_pixels_exact_rgba": 10,
        "not_reviewed": 3950,
    }
    if dict(counts) != expected:
        raise ValueError(f"Unexpected classification totals: {counts}")

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("image_path", "classification", "evidence"))
        writer.writerows(rows)
    print(f"{OUTPUT}: {dict(counts)}")


if __name__ == "__main__":
    main()
