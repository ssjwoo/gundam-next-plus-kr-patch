#!/usr/bin/env python3
"""Build a protected, context-aware handoff package for an external translator.

The package deliberately separates immutable source evidence from the fields an
external model is allowed to author.  It exports only confirmed text rows by
default and keeps unresolved text-like candidates out of the paid translation
queue.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import re
import unicodedata


TOKEN_RE = re.compile(r"~[A-Za-z0-9][A-Za-z0-9]?|%[A-Za-z]")
RESPONSE_FIELDS = ("id", "baseline", "target_ko", "status", "notes", "questions")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def source_fingerprint(record: dict) -> str:
    protected = {
        "id": record["id"],
        "source_jp": record["source_jp"],
        "source_raw_hex": record["source_raw_hex"],
        "capacity_bytes": record["capacity_bytes"],
        "protected_tokens": record["protected_tokens"],
    }
    return "sha256:" + sha256_bytes(canonical_json(protected))


def read_workbook(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_inventory(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("inventory must be a JSON list")
    inventory = {entry["id"]: entry for entry in payload}
    if len(inventory) != len(payload):
        raise SystemExit("duplicate IDs in inventory")
    return inventory


def context_view(row: dict[str, str]) -> dict[str, str]:
    value = {"id": row["id"], "source_jp": row["source_jp"]}
    if row.get("target_ko"):
        value["existing_ko_draft"] = row["target_ko"]
    return value


def source_block_reasons(text: str) -> list[str]:
    reasons = []
    unsafe = [
        f"U+{ord(char):04X} {unicodedata.category(char)}"
        for char in text
        if unicodedata.category(char).startswith("C")
    ]
    if unsafe:
        reasons.append("unresolved_control_or_private_character: " + ", ".join(sorted(set(unsafe))))
    without_tokens = TOKEN_RE.sub("", text)
    if "~" in without_tokens:
        reasons.append("unparsed_tilde_token")
    return reasons


def build_records(
    rows: list[dict[str, str]], inventory: dict[str, dict], evidence: str
) -> tuple[list[dict], list[dict], list[dict]]:
    confirmed = [row for row in rows if row.get("evidence") == evidence]
    group_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in confirmed:
        group_rows[row["group"]].append(row)

    records: list[dict] = []
    existing: list[dict] = []
    blocked: list[dict] = []
    for global_index, row in enumerate(confirmed):
        if row["id"] not in inventory:
            raise SystemExit(f"{row['id']}: missing inventory entry")
        inv = inventory[row["id"]]
        peers = group_rows[row["group"]]
        peer_index = next(i for i, peer in enumerate(peers) if peer["id"] == row["id"])
        tokens = TOKEN_RE.findall(row["source_jp"])
        base = {
            "id": row["id"],
            "group": row["group"],
            "source_order": global_index,
            "source_jp": row["source_jp"],
            "fan_english": row.get("fan_english", ""),
            "source_raw_hex": inv["raw_hex"],
            "capacity_bytes": int(row["capacity_bytes"]),
            "approx_hangul_budget": int(row["hangul_budget_if_all_double_byte"]),
            "protected_tokens": tokens,
            "context_before": [context_view(peers[peer_index - 1])] if peer_index else [],
            "context_after": (
                [context_view(peers[peer_index + 1])]
                if peer_index + 1 < len(peers)
                else []
            ),
            "context_warning": "storage order only; speaker and scene are not yet confirmed",
        }
        base["baseline"] = source_fingerprint(base)
        block_reasons = source_block_reasons(row["source_jp"])
        if block_reasons:
            blocked.append(
                {
                    "id": row["id"],
                    "group": row["group"],
                    "source_jp": row["source_jp"],
                    "reasons": block_reasons,
                    "required_action": "establish string boundary and control-token policy before translation",
                }
            )
        elif row.get("target_ko"):
            existing.append(
                {
                    "id": row["id"],
                    "source_jp": row["source_jp"],
                    "target_ko": row["target_ko"],
                    "state": row.get("status", ""),
                    "warning": "existing draft; not an approved terminology authority",
                }
            )
        else:
            records.append(base)
    return records, existing, blocked


def select_evaluation(records: list[dict], count: int) -> tuple[list[dict], list[dict]]:
    selected: list[dict] = []
    reasons: dict[str, list[str]] = defaultdict(list)

    def evenly(candidates: list[dict], limit: int) -> list[dict]:
        if limit <= 0 or len(candidates) <= limit:
            return candidates
        if limit == 1:
            return [candidates[len(candidates) // 2]]
        return [candidates[round(index * (len(candidates) - 1) / (limit - 1))] for index in range(limit)]

    def add(candidates: list[dict], reason: str, limit: int) -> None:
        added = 0
        selected_ids = {record["id"] for record in selected}
        for record in candidates:
            if record["id"] in selected_ids:
                continue
            selected.append(record)
            reasons[record["id"]].append(reason)
            selected_ids.add(record["id"])
            added += 1
            if added >= limit or len(selected) >= count:
                return

    by_group: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_group[record["group"]].append(record)
    group_representatives = [group[len(group) // 2] for group in by_group.values()]
    add(evenly(group_representatives, 12), "consumer_group_spread", 12)

    token_candidates = [record for record in records if record["protected_tokens"]]
    add(evenly(token_candidates, 4), "control_tokens", 4)

    sentence_candidates = [
        record
        for record in records
        if re.search(r"[。！？…]", record["source_jp"])
        and 8 <= len(record["source_jp"]) <= 64
    ]
    add(evenly(sentence_candidates, 8), "sentence_or_dialogue", 8)

    short_candidates = sorted(records, key=lambda record: len(record["source_jp"]))
    add(evenly(short_candidates[: max(20, len(short_candidates) // 10)], 4), "short_ui_or_name", 4)

    long_candidates = sorted(records, key=lambda record: len(record["source_jp"]), reverse=True)
    add(evenly(long_candidates[: max(20, len(long_candidates) // 10)], 4), "long_or_layout_sensitive", 4)

    remaining_slots = count - len(selected)
    if remaining_slots > 0:
        stride = max(1, len(records) // remaining_slots)
        add(records[::stride], "corpus_spread", remaining_slots)
    if len(selected) < count:
        add(records, "fill", count - len(selected))

    selected = sorted(selected[:count], key=lambda record: record["source_order"])
    evaluation = []
    for record in selected:
        value = dict(record)
        value["evaluation_reasons"] = reasons[record["id"]]
        evaluation.append(value)
    selected_ids = {record["id"] for record in selected}
    production = [record for record in records if record["id"] not in selected_ids]
    return evaluation, production


def make_batches(records: list[dict], batch_size: int) -> list[list[dict]]:
    by_group: list[list[dict]] = []
    current_group: list[dict] = []
    current_name = None
    for record in records:
        if current_name is None or record["group"] == current_name:
            current_group.append(record)
            current_name = record["group"]
        else:
            by_group.append(current_group)
            current_group = [record]
            current_name = record["group"]
    if current_group:
        by_group.append(current_group)

    batches: list[list[dict]] = []
    current: list[dict] = []
    for group in by_group:
        while len(group) > batch_size:
            if current:
                batches.append(current)
                current = []
            batches.append(group[:batch_size])
            group = group[batch_size:]
        if current and len(current) + len(group) > batch_size:
            batches.append(current)
            current = []
        current.extend(group)
    if current:
        batches.append(current)
    return batches


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def response_template(records: list[dict]) -> list[dict]:
    return [
        {
            "id": record["id"],
            "baseline": record["baseline"],
            "target_ko": "",
            "status": "",
            "notes": "",
            "questions": [],
        }
        for record in records
    ]


def prompt_text() -> str:
    return """# 외부 AI 번역 작업 지시

당신은 PSP 게임 《기동전사 건담 vs. 건담 NEXT PLUS》의 일본어 문자열을 자연스러운 한국어로 번역한다.

## 입력과 출력

- 입력은 UTF-8 JSONL이다. 한 줄이 한 항목이다.
- `source_jp`가 기준 원문이다. `fan_english`는 오역·줄 어긋남이 있을 수 있는 참고 자료일 뿐이다.
- 응답 템플릿의 여섯 필드만 채워 UTF-8 JSONL로 반환한다. 설명문이나 마크다운 코드 울타리를 덧붙이지 않는다.
- `id`와 `baseline`은 절대 변경하지 않는다.

## 번역 원칙

- 직역보다 게임 화면에서 자연스러운 한국어를 우선하되 원문의 의미, 기능, 선택 결과를 바꾸지 않는다.
- `protected_tokens`의 토큰은 철자, 인수, 개수, 순서를 그대로 유지한다.
- `approx_hangul_budget`은 현재 구현의 대략적인 길이 목표이지 의미를 잘라낼 허가가 아니다. 자연스러운 번역이 목표보다 길면 원문 의미를 보존하고 `notes`에 `길이 검토 필요`라고 적는다.
- 화자·장면이 확정되지 않아 번역이 달라질 수 있으면 추측하지 말고 `status`를 `needs_context`로 둔다.
- 고유명사나 건담 공식 용어가 불확실하면 `status`를 `needs_term_decision`으로 두고 `questions`에 후보와 쟁점을 적는다.
- 실제 텍스트가 아닌 데이터로 의심되면 `status`를 `not_text_candidate`로 두며 임의 번역하지 않는다.
- 번역 가능한 항목은 `status`를 `draft`로 둔다. 승인·완료를 뜻하는 표현은 사용하지 않는다.

## 응답 스키마

각 줄은 정확히 다음 필드만 사용한다.

```json
{"id":"EBOOT_00000","baseline":"sha256:...","target_ko":"번역문","status":"draft","notes":"","questions":[]}
```

허용 상태는 `draft`, `needs_context`, `needs_term_decision`, `not_text_candidate` 네 가지다.
"""


def readme_text(manifest: dict) -> str:
    return f"""# 외부 AI 번역 인계 패키지

권장 교환 형식은 **UTF-8 JSONL**입니다. CSV보다 줄바꿈·따옴표·전각 문자와 제어 토큰을 안전하게 보존하고, 대규모 결과에서 한 줄만 손상돼도 나머지를 회수하기 쉽습니다. XLSX는 사람의 후속 검수용으로만 쓰는 편이 안전합니다.

## 범위

- 확인된 텍스트: {manifest['counts']['confirmed_text']}개
- 기존 한국어 초안: {manifest['counts']['existing_drafts']}개
- 외부 번역 대상: {manifest['counts']['translation_queue']}개
- 1차 평가 표본: {manifest['counts']['evaluation']}개
- 평가 통과 후 본번역 대상: {manifest['counts']['production']}개
- 경계·제어코드가 불명확해 번역에서 차단한 항목: {manifest['counts']['blocked_source_structure']}개
- 현재 확인 범위 밖의 분류 대기 후보: {manifest['counts']['unconfirmed_candidates']}개

## 전달 순서

1. 다른 AI에게 `TRANSLATOR_PROMPT_KO.md`, `terminology.json`, `reference_existing_drafts.jsonl`, `evaluation/evaluation.input.jsonl`, `evaluation/evaluation.response.jsonl`을 전달합니다.
2. AI에게 `evaluation.response.jsonl`의 빈 필드만 채워 돌려달라고 합니다.
3. 사람이 표본의 정확성·말투·용어·수정 부담을 평가합니다. 평가를 통과하기 전에는 `production/` 전체를 맡기지 않습니다.
4. 통과하면 `production/batch_NNN.input.jsonl`과 같은 번호의 응답 템플릿을 한 묶음씩 전달합니다.
5. 회수한 파일은 `tools/validate_ai_translation_response.py`로 검사합니다. 기계 검증을 통과해도 번역 승인 상태는 아닙니다.

## 중요한 경계

- 입력 파일은 읽기 전용입니다. 외부 AI가 작성할 수 있는 것은 응답 파일의 `target_ko`, `status`, `notes`, `questions`뿐입니다.
- `fan_english`는 부분 영문판의 참고 번역이며 일본어 원문보다 우선하지 않습니다.
- `context_before`와 `context_after`는 저장 순서상 이웃일 뿐, 실제 장면 순서나 화자를 보증하지 않습니다.
- 주소·포인터·원시 바이트는 번역 AI가 재작성하지 않습니다. 병합 단계에서 원본 기준선과 다시 대조합니다.
- 이 패키지는 개발용 초안을 만들기 위한 것이며 배포 승인 자료가 아닙니다.
- `blocked_source_structure.jsonl`은 번역 자료가 아니라 재추출·제어코드 조사 대기열입니다.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("inventory_json", type=Path)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--evidence", default="fan_patch_modified")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--evaluation-count", type=int, default=32)
    parser.add_argument("--source-game-sha256", default="")
    args = parser.parse_args()

    if args.batch_size < 1 or args.evaluation_count < 1:
        raise SystemExit("batch size and evaluation count must be positive")
    if args.outdir.exists() and any(args.outdir.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output directory: {args.outdir}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    rows = read_workbook(args.workbook)
    inventory = read_inventory(args.inventory_json)
    records, existing, blocked = build_records(rows, inventory, args.evidence)
    if args.evaluation_count >= len(records):
        raise SystemExit("evaluation count must be smaller than the translation queue")
    evaluation, production = select_evaluation(records, args.evaluation_count)
    batches = make_batches(production, args.batch_size)

    evaluation_dir = args.outdir / "evaluation"
    production_dir = args.outdir / "production"
    evaluation_dir.mkdir()
    production_dir.mkdir()

    evaluation_input = evaluation_dir / "evaluation.input.jsonl"
    evaluation_response = evaluation_dir / "evaluation.response.jsonl"
    write_jsonl(evaluation_input, evaluation)
    write_jsonl(evaluation_response, response_template(evaluation))

    batch_manifest = []
    for index, batch in enumerate(batches, 1):
        stem = f"batch_{index:03d}"
        input_path = production_dir / f"{stem}.input.jsonl"
        response_path = production_dir / f"{stem}.response.jsonl"
        write_jsonl(input_path, batch)
        write_jsonl(response_path, response_template(batch))
        batch_manifest.append(
            {
                "name": stem,
                "entries": len(batch),
                "first_id": batch[0]["id"],
                "last_id": batch[-1]["id"],
                "input_sha256": sha256_file(input_path),
            }
        )

    write_jsonl(args.outdir / "reference_existing_drafts.jsonl", existing)
    write_jsonl(args.outdir / "blocked_source_structure.jsonl", blocked)
    terminology = {
        "schema_version": 1,
        "authority": "No project-wide terminology is approved yet.",
        "entries": [],
        "instruction": "Flag uncertain names and series terms as needs_term_decision; do not silently invent a global rule.",
    }
    (args.outdir / "terminology.json").write_text(
        json.dumps(terminology, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.outdir / "TRANSLATOR_PROMPT_KO.md").write_text(prompt_text(), encoding="utf-8")

    confirmed_count = sum(row.get("evidence") == args.evidence for row in rows)
    unconfirmed_candidates = len(rows) - confirmed_count
    manifest = {
        "schema_version": 1,
        "source_game_sha256": args.source_game_sha256.upper(),
        "workbook_sha256": sha256_file(args.workbook),
        "inventory_sha256": sha256_file(args.inventory_json),
        "selection": {
            "required_evidence": args.evidence,
            "skip_rows_with_existing_target": True,
            "evaluation_before_production": True,
        },
        "response_fields": list(RESPONSE_FIELDS),
        "allowed_status": ["draft", "needs_context", "needs_term_decision", "not_text_candidate"],
        "counts": {
            "workbook_candidates": len(rows),
            "confirmed_text": confirmed_count,
            "existing_drafts": len(existing),
            "translation_queue": len(records),
            "evaluation": len(evaluation),
            "production": len(production),
            "blocked_source_structure": len(blocked),
            "unconfirmed_candidates": unconfirmed_candidates,
            "production_batches": len(batches),
        },
        "evaluation_input_sha256": sha256_file(evaluation_input),
        "batches": batch_manifest,
    }
    (args.outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.outdir / "README_KO.md").write_text(readme_text(manifest), encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
