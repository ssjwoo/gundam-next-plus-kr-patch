#!/usr/bin/env python3
"""Build a review handoff for the machine-translated rows.

Two kinds of work come out of the machine pass:

  * ``machine_draft_overflow`` - the draft does not fit the fixed byte slot, so
    the row still shows the original Japanese and has to be shortened.
  * ``translated`` with an MT note - the draft ships today and needs a quality
    pass.

The Excel file is the human/model-facing artefact; the ``batch_NNN.input.jsonl``
files use the same protected-token + baseline contract as
``tools/prepare_ai_translation_handoff.py`` so the answers can be checked with
``tools/validate_ai_translation_response.py`` and merged back.

Measured facts, not guesses: the original bytes are the source text encoded as
CP932 (that is how the game stores it), a Korean syllable costs two bytes, and
ASCII plus the ``%x``/``~pS`` tokens cost one each.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_hangul_poc import encode_hangul  # noqa: E402

TOKEN_RE = re.compile(r"~[A-Za-z0-9][A-Za-z0-9]?|%[A-Za-z]")
# A real Japanese string has a kana run, a hiragana, or a kanji compound.
# Random bytes that happen to decode as CP932 rarely do.
REAL_TEXT_RE = re.compile(r"[\u3040-\u30ff]{2,}|[\u3041-\u309f]|[\u4e00-\u9fff]{2,}")
BATCH_SIZE = 100
MT_NOTE_PREFIX = "MT draft"


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sanitize(value: object) -> str:
    """Excel refuses control characters, and the rejected candidates are full of
    them, so show them as escapes instead of dropping the row."""
    text = "" if value is None else str(value)
    out = []
    for char in text:
        code = ord(char)
        if char == "\n":
            out.append("\\n")
        elif code < 0x20 or code == 0x7F:
            out.append(f"\\x{code:02X}")
        else:
            out.append(char)
    return "".join(out)


def source_fingerprint(record: dict) -> str:
    protected = {
        "id": record["id"],
        "source_jp": record["source_jp"],
        "source_raw_hex": record["source_raw_hex"],
        "capacity_bytes": record["capacity_bytes"],
        "protected_tokens": record["protected_tokens"],
    }
    return "sha256:" + hashlib.sha256(canonical_json(protected)).hexdigest()


def task_of(row: dict) -> str | None:
    status = row["status"]
    if status == "machine_draft_overflow":
        return "shorten"
    if status == "machine_draft_unsupported":
        return "unsupported"
    if status == "translated" and (row.get("note") or "").startswith(MT_NOTE_PREFIX):
        return "polish"
    return None


def slot_state(elf: bytes, offset: int, capacity: int, raw: bytes, encoded: bytes) -> str:
    """Whether this row's translation is actually in the shipped ELF."""
    span = capacity + 1
    current = elf[offset : offset + span]
    if encoded and current.startswith(encoded) and not any(current[len(encoded) :]):
        return "적용됨"
    if (current.startswith(raw) and current[len(raw)] == 0
            and not any(current[len(raw) + 1 :])):
        return "미적용"
    return "다른 경로로 번역됨"


def build_rows(workbook: Path, elf: bytes | None) -> tuple[list[dict], list[dict]]:
    with workbook.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_group: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_group[row["group"]].append(row)

    work: list[dict] = []
    excluded: list[dict] = []
    for row in rows:
        task = task_of(row)
        if task is None:
            if row["status"] == "todo":
                excluded.append({
                    "id": row["id"],
                    "group": row["group"],
                    "source_jp": row["source_jp"],
                    "evidence": row["evidence"],
                    "reason": "CP932 round-trip failed or no kana: not a real string",
                })
            continue
        source = row["source_jp"]
        capacity = int(row["capacity_bytes"])
        raw = source.encode("cp932")
        encoded = b""
        issue = ""
        try:
            encoded = encode_hangul(row["target_ko"])
        except ValueError as exc:
            issue = str(exc)
        if task == "shorten" or (encoded and len(encoded) > capacity):
            issue = (f"{len(encoded) - capacity}바이트 초과 "
                     f"(초안 {len(encoded)} / 슬롯 {capacity})")
        peers = by_group[row["group"]]
        index = next(i for i, peer in enumerate(peers) if peer["id"] == row["id"])
        record = {
            "id": row["id"],
            "group": row["group"],
            "source_order": index,
            "source_jp": source,
            "fan_english": row.get("fan_english") or "",
            "source_raw_hex": raw.hex(" "),
            "capacity_bytes": capacity,
            "approx_hangul_budget": int(row["hangul_budget_if_all_double_byte"]),
            "protected_tokens": TOKEN_RE.findall(source),
            "context_before": [{"id": peers[index - 1]["id"],
                                "source_jp": peers[index - 1]["source_jp"]}] if index else [],
            "context_after": [{"id": peers[index + 1]["id"],
                               "source_jp": peers[index + 1]["source_jp"]}]
            if index + 1 < len(peers) else [],
            "context_warning": "storage order only; speaker and scene are not yet confirmed",
        }
        record["baseline"] = source_fingerprint(record)
        applied = ""
        if elf is not None:
            applied = slot_state(elf, int(row["file_offset_hex"], 16), capacity,
                                 raw, encoded if task != "unsupported" else b"")
        record.update({
            "task": task,
            "mt_draft": row["target_ko"],
            "encoded_bytes": len(encoded),
            "max_hangul": capacity // 2,
            "slack_bytes": capacity - len(encoded),
            "existing_status": row["status"],
            "applied": applied,
            "issue": issue,
            "real_text": "예" if REAL_TEXT_RE.search(source) else "아니오",
        })
        if not REAL_TEXT_RE.search(source):
            record["task"] = task  # keep the task label, but rank it last
        work.append(record)

    order = {"shorten": 0, "polish": 1, "unsupported": 2}
    work.sort(key=lambda item: (0 if item["real_text"] == "예" else 1,
                                order[item["task"]], item["id"]))
    return work, excluded


def write_batches(work: list[dict], outdir: Path) -> list[str]:
    fields = ("id", "group", "source_order", "source_jp", "fan_english",
              "source_raw_hex", "capacity_bytes", "approx_hangul_budget",
              "protected_tokens", "context_before", "context_after",
              "context_warning", "baseline")
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for start in range(0, len(work), BATCH_SIZE):
        chunk = work[start : start + BATCH_SIZE]
        name = f"batch_{start // BATCH_SIZE + 1:03d}.input.jsonl"
        with (outdir / name).open("w", encoding="utf-8") as handle:
            for item in chunk:
                handle.write(json.dumps({key: item[key] for key in fields},
                                        ensure_ascii=False) + "\n")
        written.append(name)
    return written


def write_excel(work: list[dict], excluded: list[dict], out: Path, workbook: Path) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    book = openpyxl.Workbook()

    guide = book.active
    guide.title = "안내"
    lines = [
        ("이 파일은 무엇인가", "NEXT PLUS 한국어 패치의 기계번역 초안을 다듬기 위한 인계 문서입니다."),
        ("", ""),
        ("작업 시트", "'번역검토' 시트의 각 행을 보고 Q열(수정안)에 한국어를 적어 주세요."),
        ("", "B열(진짜 문자열)은 휴리스틱입니다: 가나·한자가 있으면 '예', 우연히 CP932로 읽힌 바이너리로 보이면 '아니오'."),
        ("", "'아니오' 91행은 회색으로 표시해 맨 뒤로 보냈습니다. 건너뛰어도 됩니다."),
        ("", "L열(고칠 이유)에 무엇을 고쳐야 하는지 적혀 있습니다."),
        ("", ""),
        ("가장 중요한 규칙", "번역문을 게임의 고정 슬롯에 넣어야 합니다. 한글 1자 = 2바이트, ASCII 1자 = 1바이트입니다."),
        ("", "G열(슬롯 바이트)을 넘기면 그 행은 적용되지 않고 원문 일본어로 남습니다."),
        ("", "H열(최대 한글)은 슬롯을 전부 한글로 채웠을 때의 글자 수입니다. 이보다 짧게 쓰면 안전합니다."),
        ("", ""),
        ("쓸 수 있는 문자", "ASCII(0x20~0x7E)와 한글 음절(U+AC00~U+D7A3)만 됩니다."),
        ("", "'·' '—' '…' '「」' '☆' 같은 문자는 코덱이 거부합니다. ASCII 구두점(., !, ?, -, ~, [], ...)으로 바꿔 주세요."),
        ("", "한글 음절 중 '겙'(U+AC99), '겚'(U+AC9A), '겥'(U+ACA5) 세 글자는 특수문자(☆★▼) 자리라 쓸 수 없습니다."),
        ("", ""),
        ("보존 토큰", "`%t` `%d` `%s` `%r` `%n` `%m` `~pS` `~pE` 같은 토큰은 게임이 실행 중에 치환합니다."),
        ("", "L열(보존 토큰)의 토큰은 반드시 그대로 남겨 주세요. 빠지거나 바뀌면 적용이 거부됩니다."),
        ("", ""),
        ("작업 종류", "shorten  = 초안이 슬롯보다 길어서 지금 원문 일본어가 나옵니다. 줄여 주세요."),
        ("", "polish   = 이미 적용돼 있지만 기계번역이라 품질을 봐야 합니다. 다듬어 주세요."),
        ("", "unsupported = 초안에 코덱이 거부하는 문자가 있습니다. 그 문자만 바꾸면 됩니다(수정안이 필요합니다)."),
        ("", ""),
        ("문체", "원문은 일본어 게임 문장입니다. 짧은 UI 라벨은 명사형으로, 대사는 존댓말/평서문을 원문에 맞춰 주세요."),
        ("", "고유명사(기체명·인물명)는 팬 번역 관례를 따르고, D열(영어 팬번역)을 참고하세요."),
        ("", ""),
        ("숫자", "이 패치는 숫자 글리프를 한글로 읽도록 바꿔 놓았습니다. 수량·시간은 '육십초', '두 기'처럼 한글 수사로 적습니다."),
        ("", "단, 원문에 ASCII 숫자가 그대로 있는 경우는 그대로 두어도 됩니다(E열 참고)."),
        ("", ""),
        ("응답 형식", "JSONL로 받으려면 같은 폴더의 batch_*.input.jsonl을 쓰고 응답은 "
                 "{id, baseline, target_ko, status, notes, questions} 형식으로 주세요."),
        ("", "status는 draft/approved 중 하나입니다. baseline은 입력의 값을 그대로 돌려주세요."),
        ("", ""),
        ("검증 방법", "python tools/validate_ai_translation_response.py <input.jsonl> <response.jsonl>"),
        ("", "python tools/merge_dev_translation_responses.py ... 로 병합한 뒤 재빌드합니다."),
        ("", ""),
        ("참고", f"원본 워크북: {workbook.name}"),
        ("", f"작업 행 수: {len(work)}   제외 행 수: {len(excluded)}"),
    ]
    guide.column_dimensions["A"].width = 18
    guide.column_dimensions["B"].width = 120
    for row_index, (key, value) in enumerate(lines, start=1):
        guide.cell(row=row_index, column=1, value=sanitize(key)).font = Font(bold=bool(key))
        cell = guide.cell(row=row_index, column=2, value=sanitize(value))
        cell.alignment = Alignment(wrap_text=False, vertical="top")

    sheet = book.create_sheet("번역검토")
    headers = ["작업", "진짜 문자열", "적용 상태", "id", "그룹", "원문(일본어)", "영어 팬번역",
               "슬롯 바이트", "최대 한글", "기계번역 초안", "현재 바이트", "고칠 이유",
               "보존 토큰", "앞 문맥", "뒤 문맥", "수정안", "메모"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F6228")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    fills = {"shorten": "FCE4D6", "polish": "DDEBF7", "unsupported": "EDEDED"}
    for item in work:
        sheet.append([sanitize(value) for value in [
            item["task"],
            item["real_text"],
            item["applied"],
            item["id"],
            item["group"],
            item["source_jp"],
            item["fan_english"],
            item["capacity_bytes"],
            item["max_hangul"],
            item["mt_draft"],
            item["encoded_bytes"],
            item["issue"],
            " ".join(item["protected_tokens"]),
            item["context_before"][0]["source_jp"] if item["context_before"] else "",
            item["context_after"][0]["source_jp"] if item["context_after"] else "",
            "",
            "",
        ]])
        row_index = sheet.max_row
        sheet.cell(row=row_index, column=1).fill = PatternFill(
            "solid", fgColor=fills[item["task"]])
        if item["task"] == "shorten":
            sheet.cell(row=row_index, column=16).fill = PatternFill("solid", fgColor="FFF2CC")
        elif item["applied"] == "다른 경로로 번역됨":
            sheet.cell(row=row_index, column=17).value = (
                "이 슬롯은 미션/맵 번역이 이미 채웠습니다(워크북 값은 화면에 안 나감)")
        if item["real_text"] == "아니오":
            sheet.cell(row=row_index, column=2).fill = PatternFill("solid", fgColor="D9D9D9")
    widths = [10, 11, 14, 14, 16, 34, 22, 11, 10, 38, 11, 26, 14, 26, 26, 38, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "E2"
    sheet.auto_filter.ref = f"A1:Q{sheet.max_row}"

    junk = book.create_sheet("제외된행")
    junk.append(["id", "그룹", "원문(일본어)", "근거", "제외 이유"])
    for cell in junk[1]:
        cell.font = Font(bold=True)
    for item in excluded:
        junk.append([sanitize(item["id"]), sanitize(item["group"]),
                     sanitize(item["source_jp"]), sanitize(item["evidence"]),
                     sanitize(item["reason"])])
    for index, width in enumerate([14, 16, 40, 26, 46], start=1):
        junk.column_dimensions[get_column_letter(index)].width = width
    junk.freeze_panes = "A2"

    out.parent.mkdir(parents=True, exist_ok=True)
    book.save(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--name", default="next_plus_mt_review_2026-09-26")
    parser.add_argument("--elf", type=Path,
                        help="shipped ELF; lets each row say whether it is applied")
    args = parser.parse_args()

    work, excluded = build_rows(args.workbook, args.elf.read_bytes() if args.elf else None)
    args.outdir.mkdir(parents=True, exist_ok=True)
    excel = args.outdir / f"{args.name}.xlsx"
    write_excel(work, excluded, excel, args.workbook)
    batches = write_batches(work, args.outdir / args.name)
    counts: dict[str, int] = defaultdict(int)
    for item in work:
        counts[item["task"]] += 1

    summary = {
        "workbook": str(args.workbook),
        "excel": str(excel),
        "batch_dir": str(args.outdir / args.name),
        "batches": len(batches),
        "rows": len(work),
        "by_task": dict(counts),
        "excluded_rows": len(excluded),
        "total_slack_shortfall_bytes": -sum(
            item["slack_bytes"] for item in work if item["slack_bytes"] < 0),
    }
    (args.outdir / f"{args.name}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
