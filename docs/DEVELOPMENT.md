# 개발·복구 안내

현재 정식 릴리스는 **v1.0.0**, 내부 빌드 기준은 **042**입니다. 사용자가 042를 간단히 플레이하고 정식 배포를 승인했습니다. 이 확인은 전체 게임 완주나 한글화 전수 검수와 구분합니다. 실제 로컬 입력과 다음 작업은 [현재 인계](../99_HANDOFF/CURRENT.md), 결과 집계는 [status.json](../reports/status.json)을 먼저 읽으세요. 아래 과거 복구 절차는 최신 빌드 전체를 재생성하는 단일 명령이 아닙니다.

## 환경

Python 3.11 이상과 프로젝트 Python 의존성을 사용합니다. ISO 도구는 [hanpatch](https://github.com/yazzang-homelab/hanpatch)의 PSP 모듈에 의존합니다. 이미지 배경 복원은 선택적 `requirements-graphics.txt` 환경을 사용합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
git clone https://github.com/yazzang-homelab/hanpatch.git ..\hanpatch
.\.venv\Scripts\python.exe -m pip install -e ..\hanpatch
```

기존 작업 환경이 있다면 재설치하거나 작업 폴더를 초기화하지 않습니다. 원본 ISO·폰트 입력·추출 파일·연결 계획과 실제 검수 자료는 로컬에서 준비하며 Git에 포함하지 않습니다. 공개 한국어 카탈로그만으로 원문 소유권과 빌드 입력을 모두 복원할 수는 없습니다.

## 도구와 검증 경계

| 작업 | 주요 도구 |
|---|---|
| 원본·슬롯 조사 | `inventory_eboot_text.py`, `parse_next_plus_mission_records.py`, `recover_source_workbook.py` |
| 텍스트 삽입 | `apply_workbook_slots.py`, `prepare_residual_text_plan.py`, `build_text_data_revision_iso.py` |
| 폰트·코덱 | `make_hangul_poc.py`, `make_pgf_from_ttf.py`, `extend_pgf_glyphs.py`, `repair_font_path_ctype.py` |
| 이미지 | `inspect_gim.py`, `render_localized_labels.py`, `replace_gim_picture.py`, `repack_pzz.py`, `build_graphics_revision_iso.py` |
| 쓰기 보호 | `nontext_protection.py`, `text_control_guard.py`, `text_literal_ownership.py`, `verify_original_title_logos.py` |
| 패치 재적용 | `make_verified_original_delta.py` |

도구는 `tools/`에 있으며 인자는 각각의 `--help`로 확인합니다. 빌드마다 정확한 입력 해시·원문 바이트·슬롯 용량·폰트·제어 토큰·포인터를 검증하고 새 출력 경로를 사용합니다. 마지막으로 ISO에서 실제로 다시 읽은 결과와 허용된 변경 범위를 대조합니다. 이미지 도구의 원본 팔레트·할당·보호 픽셀 검사와 PZZ 마지막 16바이트 검사값을 생략하지 않습니다.

원판 기반 xdelta는 재적용 출력 스트림의 크기·SHA-256으로 검사해 중복 ISO를 만들지 않습니다. 게임 실행과 장면 검수는 사용자가 맡습니다. 정적 검사나 격리 함수 시험을 게임 실행 성공으로 기록하지 않습니다.

## 과거 패치 복구

2026-10-02 복구 입력은 다음 두 ISO였습니다. 최신 패치를 이 보관 패치에 덧씌우지 않습니다.

| 입력 | SHA-256 |
|---|---|
| 일본판 원본 | `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3` |
| 사용자가 보관한 패치 | `c0e2ac8154cf240649229a95bcf2a52f37688096ae2918e16c7857c1491a4992` |

복구 도구는 복호화한 원본 ELF, 재구성한 공개 v19 ELF, 보관 패치 ELF와 원본 인벤토리를 대조합니다. 원본 EBOOT 복호화에는 선택적 `pyeboot==0.2.3`을 사용했습니다. `analysis/v19.elf`는 v19 xdelta를 원판에 적용한 뒤 EBOOT을 추출해 준비합니다.

이미 삽입된 표현을 찾을 때는 현재 번역이 아닌 [수정 전 고정 초안](../translations/baselines/README.md)을 입력합니다. 일반 번역 편집은 현재 카탈로그를 사용합니다.

```powershell
.\.venv\Scripts\python.exe tools\recover_source_workbook.py analysis\original_decrypted_eboot.elf analysis\v19.elf analysis\provided\PSP_GAME\SYSDIR\EBOOT.BIN analysis\eboot_inventory\eboot_text_inventory.json translations\baselines\development_draft_2026-09-26_ko_only_pre_polish.jsonl work\recovered --mission-records work\next_plus_mission_handoff_v2\structural_records.jsonl
```

이 명령은 당시 추출 입력과 구조 레코드가 준비된 경우의 복구 절차입니다. 원문 주소·바이트·포인터를 확인하며 스캐너 ID만으로 연결하지 않습니다. 현재 슬롯 근거는 [현재 한국어 카탈로그](../translations/current_bound_text_ko_2026-10-08.json)와 [읽기 검사](../reports/current_text_readback_2026-10-08.json)에 있습니다.

숫자 수정용 `repair_fixed_width_digits.py`·`build_digit_repair_iso.py`는 당시의 특정 ELF·폰트·보관 ISO 해시만 받아들입니다. 과거 v10_base·텍스트 002·005·020 빌드 명령을 현재 042에 무조건 재사용하면 이후 수정이 누락됩니다. 당시 전체 명령은 [통합 전 문서](https://github.com/ssjwoo/gundam-next-plus-kr-patch/blob/78269664824c0ad91e71d5f59f6c3f209f53202c/docs/UPDATE_2026-10-02.md)에 보존돼 있습니다.

## 재발 방지

- 문자열 시작과 포인터가 가리키는 전체 문장 경계를 확인합니다. 문자열 중간을 시작점으로 디코딩한 오류를 실제 전체 문자열 결함으로 세지 않습니다.
- 수치·벡터·포인터·내장 PNG·숫자 테이블을 번역하지 않습니다. `~`와 게임 제어 토큰도 일반 구두점으로 취급하지 않습니다.
- `.data`의 0 구간을 빈 공간으로 추정해 폰트 경로를 넣지 않습니다. 원본 문자 분류표 257바이트를 보호합니다.
- 폰트 헤더 정렬 값·센티넬·예약 인덱스와 고정 2바이트 숫자 폭을 유지합니다. [세부 구조](RESEARCH_NOTES.md).
- 타이틀 로고는 원본 픽셀·색상 인덱스로 유지하고 일반 한글 UI를 보호합니다. [로고 정책](GUNDAM_TITLE_LOGO_POLICY.md).
- 게임·에뮬레이터·종료된 CMD 검증을 AI가 실행하거나 반복 요청하지 않습니다. 임시 파일은 검증 후 정리하되 원본·현재 후보·재현 입력을 보존합니다.

## 번역 자료

공개 자료는 한국어 초안과 검수 상태를 담습니다. `development_draft_2026-09-26_ko_only.jsonl`의 4,271행이나 오래된 숫자 ID를 현재 게임의 전체 번역·승인·삽입 완료 증거로 쓰지 않습니다. 원문·원시 바이트·전체 워크북·일본어 인계 패키지는 로컬에 둡니다.

2026-10-02 검수의 변경 전후·파일 해시·보류 항목은 [검수 보고서](../reports/translation_review_2026-10-02.json)에 있습니다. 최신 원문 경계 확인과 개별 보정은 `translations/current_bound_text_ko_2026-10-08.json` 및 개별 수정 카탈로그를 함께 사용합니다.

042의 간단 플레이는 사용자가 확인했습니다. 전체 게임·NEXT PLUS 한글화 완료와 전체 플레이 검수는 별도 후속 범위입니다. [진행 현황](../PROGRESS.md), [백식 미션 해결 기록](MISSION_FREEZE_027_2026-10-05.md), [배포 방침](PUBLICATION_POLICY.md).

## 040–042 감독 검수 재현

공개 규칙은 `translations/web_ai_supervised_text_040_2026-10-08.json`과 `translations/graphics/web_ai_supervised_040_2026-10-08.json`, `web_ai_supervised_041_2026-10-08.json`, `web_ai_supervised_042_2026-10-08.json`입니다. 전체 원문·패킷 그림·native 바인딩·폰트와 기준 ISO는 로컬에 보관합니다.

`prepare_residual_text_plan.py --owned-catalog`는 기준 ELF/원판 해시가 일치하는 소유권 카탈로그를 추가로 받습니다. 실제 리터럴과 NUL만 소유하는 슬롯에 인접 정렬 패딩을 빌려주지 않으며 주소·용량·원문 해시·포인터·기준 한글·폰트·비텍스트 보호를 모두 검사합니다. 출력 바이트 계획은 비공개입니다.

`build_supervised_graphics_batch.py`는 공개 편집 규칙, 기준 ISO, 로컬 AFS 인벤토리, 폰트, 새 출력 폴더를 인자로 받습니다. 규칙의 ISO·폰트·패킷 바인딩 해시를 검증하고 정확한 그림 칸만 교체해 native 재읽기·팔레트·나머지 모델 데이터·고정 PZZ 구조와 검사값을 확인합니다. 이후 `build_graphics_revision_iso.py`와 `make_verified_original_delta.py`로 새 ISO와 원판용 패치를 만듭니다. 040→041→042의 중간 ISO는 해당 원판용 xdelta로 재구성할 수 있습니다.
