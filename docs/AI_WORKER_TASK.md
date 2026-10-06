# 다른 AI 작업 임무 — 잔여 한글화 조사·부분 수정

당신은 PSP 『기동전사 건담: 건담 VS. 건담 NEXT PLUS』 한글화의 **조사·부분 수정 담당 AI**다. 감독 AI가 결과를 독립 검수하고 최신 패치에 통합·빌드한다. 사용자는 실제 게임 검수를 맡는다. 먼저 기존 자료를 읽고 수행 가능한 작업부터 실행하라. 최종 ISO 제작·릴리스 게시·프로젝트 공통 상태 변경은 감독 AI에게 맡긴다.

## 1. 기준과 목표

작업 기준은 **038**이다. 원판 기반 누적 xdelta가 공개됐고 정적 검사·재적용·공개 다운로드 확인은 PASS다. 038 실행은 NOT_TESTED이며 전체 한글화 완료 판정은 없다. 마지막 사용자 수용 기준은 023이다.

| 기준 | SHA-256 |
|---|---|
| NPJH50107 일본/아시아판 원본 ISO | `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3` |
| 현재 038 ISO | `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2` |
| 현재 038 ELF | `f8e634128ef2c81f243a0edef60e2edaf7a698285bf68cc40a29ee7acec3a842` |
| 현재 폰트 | `ab8aeb1aa4d715a8a77432341b51983e923efd551ebdd9c1bfc99d70548aef22` |

첫 우선순위는 **메인 모드 선택 화면·NEXT PLUS의 미번역 일반 UI 이미지와 상태별 변형**이다. 이미 수정한 항목을 다시 만들지 말고 실제 038에서 확인한다. 일반 글꼴의 작품명·기체·파일럿명은 번역 대상이지만, **모든 건담 작품·게임의 장식 타이틀 로고는 원본 유지**다.

현재 원본에는 PZZ 2,125개·GIM 4,272면이 있고 통합 수정은 PZZ 705개·892면이다. 단순 뺄셈으로 미번역 수를 계산하지 않는다. 많은 그림에는 번역할 글자가 없고, 같은 그림을 여러 모드가 공유한다. 실제 남은 번역 수는 조사 결과로 산출한다.

## 2. 읽을 파일 — 프로젝트 루트 기준

### 먼저 읽기

1. `99_HANDOFF/CURRENT.md`: 현재 기준·열린 문제·다음 작업·사용자 지시.
2. `PROGRESS.md`, `docs/DEVELOPMENT.md`, `docs/RESEARCH_NOTES.md`: 현재 단계·도구·인코딩·구조.
3. `docs/GUNDAM_TITLE_LOGO_POLICY.md`, `docs/MISSION_FREEZE_027_2026-10-05.md`: 보호 대상과 미확인 오류.
4. `reports/graphics_scope_2026-10-05.json`, `reports/development_038_2026-10-05.json`, `reports/current_text_readback_2026-10-05.json`: 현재 검사 범위.
5. `translations/graphics/original_gundam_title_logos.json`, `translations/current_bound_text_ko_2026-10-05.json`: 보호 로고와 현재 연결 텍스트.

### 실제 작업 입력 — 로컬 프로젝트에서 읽기

- `PROJECT_STATE.json`, `work/remaining_2026-10-05/checkpoint.json`: 현재 입력·기존 작업 증거.
- 원판 `Kidou Senshi Gundam - Gundam vs. Gundam Next Plus (Japan, Asia).iso`와 `build/graphics_revision_2026-10-05/next_plus_graphics_revision_038.iso`.
- `work/remaining_2026-10-04/afs_members.json`: 원본 AFS 인덱스·파일명·할당. 일부 레코드에는 SHA-256이 없으므로 필요한 멤버의 실제 바이트를 읽어 보완한다.
- `work/remaining_2026-10-05/asset_families.json`: 계열 탐색용 보조 목록. 이름만으로 화면·모드 관계를 확정하지 않는다.
- `work/remaining_2026-10-04/checkpoint.json`, `merged_manifest_027.json`: 이미 통합한 배치. 027 당시 기록을 038 전체의 증거로 오인하지 않는다.
- `work/next_plus_graphics_2026-10-02/core/extraction_manifest.json`, `resource_reachability/`의 JSON: 기존 소스 추출·리소스 참조 조사.
- `work/remaining_2026-10-05/stage_v1.private.json`, `translations/stage_selection_graphics_ko_2026-10-05.json`: 038에 반영한 vsel01 3면·36문구. 재작업 대상이 아니라 참고다.
- 텍스트 보조 조사 시 `work/remaining_2026-10-05/canonical_text_slots_038.private.json`, `canonical_text_audit.private.json`, `candidate_038.elf` 및 원본 복호화 ELF.

파일 목록·존재 여부는 전달 묶음의 `FILE_INDEX.json`을 확인하라. 예전 `analysis/gim_render_all_v2/render_manifest.json`과 분류 CSV는 현재 없다. 옛 분류 스크립트를 그대로 실행하지 말고 필요한 소스만 새 작업 폴더에 추출·렌더링하라. GitHub와 문서 묶음에는 원본 ISO·ELF·PNG·PZZ가 포함되지 않는다. 프로젝트에 접근할 수 없다면 가능한 자료 조사와 필요한 입력 목록까지 수행하고 실제 수정·검증을 했다고 주장하지 마라.

## 3. 실행 순서

1. 원판과 038을 구분하고 첫 수정 대상의 실제 입력 해시를 확인한다. `original_jp_.iso`는 사용자가 보관한 패치본이며 원판이 아니다.
2. 기존 검토 기록과 038의 수정 상태를 대조해 조사 대기 목록을 만든다. 새 배치에서 10~20개 PZZ의 모든 GIM 그림·관련 글자 셀을 개별 검토한다. 계열 대표 이미지로 나머지를 분류하지 않는다.
3. 각 그림을 `already_localized`, `needs_translation`, `no_text`, `preserve_logo`, `uncertain`으로 구분한다. 같은 그림에서 로고와 일반 글자가 혼합되면 영역별로 기록한다. `uncertain`을 완료로 세지 않는다.
4. `needs_translation`은 일본어 UI 위치와 원문 의미를 확인하고 자연스러운 한국어를 제안한다. 애매한 작품·기체·파일럿 표기는 기존 현재 카탈로그와 실제 소스 문맥으로 연결한다.
5. 해당 파일이 NEXT PLUS 또는 메인 화면에서 사용된다는 근거를 찾는다. AFS 인덱스·요청 ID·참조 코드·메시/UV 셀 등 증거를 붙이고 모드 관계가 미확정이면 그대로 표시한다.
6. 근거가 확인된 **최대 5~10면의 작은 배치**를 수정한다. 038의 기존 한국어·로고·다른 그림을 유지하면서 글자 영역만 교체한다. 팔레트·스위즐·GIM/PZZ 크기·고정 할당·마지막 16바이트 검사값을 검증한다.
7. 자신의 출력 파일을 다시 열어 한국어·잘림·변경 영역·보호 픽셀·컨테이너 구조를 확인하고 결과와 재현 절차를 제출한다. 수정 가능한 실제 누락을 찾지 못했다면 조사표와 미확정 근거를 제출한다. 작업량을 채우기 위해 정상 리소스를 바꾸지 않는다.

필요 도구는 `tools/inspect_gim.py`, `render_pzz_gims.py`, `inspect_pmf2_ui_consumers.py`, `extract_graphic_members.py`, `render_localized_labels.py`, `replace_gim_picture.py`, `repack_pzz.py`, `pzz_integrity.py`, `verify_original_title_logos.py`다. 먼저 `--help`·현재 코드의 입출력 형식을 확인한다. 추출기가 요구하는 원본 멤버 해시가 없는 인벤토리를 임의의 값으로 통과시키지 않는다.

## 4. 텍스트·프리징은 별도 취급

미션 274개는 한글 레코드가 삽입됐으나 게임 전체 텍스트 완료는 아니다. 기존 번역 초안의 숫자 ID를 현재 슬롯에 그대로 쓰지 않는다. 실제 문자열 시작·NUL·포인터·전체 문장·폰트 코드를 확인한다. 문장 중간의 디코딩 실패나 `unowned` 분류는 확정 손상 증거가 아니다.

027에서 백식 호위 임무의 랜덤 전투 프리징이 보고됐다. 팀은 뉴 건담/아무로와 사자비/샤아다. 038에 확인한 데이터·문자 결함을 고쳤지만 실제 미션 해결은 미확인이다. 이미지 작업과 추측성 프리징 수정을 섞지 않는다. 관련 결함을 발견하면 증거·최소 수정 제안만 별도 제출하고, 감독 AI가 통합 범위를 결정한다.

## 5. 역할·쓰기 범위

- 새 파일은 자신의 `work/ai_worker_output_2026-10-06/batch_001/` 아래에만 쓴다. 도구 개선은 그 안의 새 스크립트 또는 검토 가능한 diff로 제출한다.
- 원판·038·023·027·비교용 033, 기존 소스·워크북·공통 상태·Git 브랜치를 덮거나 삭제하지 않는다. 기존 그래픽과 텍스트 복원 작업을 되돌리지 않는다.
- 자신의 검증 완료 임시 파일만 정리한다. 대용량 ISO 복제·전체 그림 재렌더링을 습관적으로 반복하지 않는다.
- 게임·에뮬레이터·CMD를 실행하거나 사용자에게 반복 검수를 요구하지 않는다. 실제 실행 판정은 `NOT_TESTED`로 유지한다.
- Git push·릴리스 업로드·최종 ISO/xdelta 제작은 하지 않는다. 감독 AI가 결과를 검수하고 통합·빌드한다.
- 사용량을 실제 조회할 수 있다면 5시간 한도 잔여 30%에서 새 작업을 멈추고 진행 중 배치·근거·다음 작업을 인계한다. 다른 서비스의 한도를 임의로 같은 숫자로 환산하지 않는다.

## 6. 제출물·완료 조건

출력 폴더에 다음 파일을 만든다. 해당 작업을 하지 않았다면 빈 성공 보고서 대신 수행하지 않은 이유를 적는다.

| 파일 | 필수 내용 |
|---|---|
| `SUMMARY_KO.md` | 무엇을 확인·수정했는지, 실제 남은/미확정 대상, 재현 명령, 필요한 입력 |
| `coverage.csv` | 멤버명·AFS 인덱스·part·picture·분류·일본어 글자 영역·모드 관계·개별 근거 |
| `translations.json` | 안정 ID·현재 원본 위치·문맥·한국어·글자 칸. 실제 텍스트면 전체 문자열 경계·포인터·제어 토큰 |
| `delivery_manifest.json` | 기준 038 해시, 읽은 입력과 생성 파일의 상대 경로·크기·SHA-256, 정확한 변경 단위·통합 순서 |
| `verification.json` | 실제 실행한 정적 검사·보호 영역 변경 수·팔레트/할당/PZZ 검사값·읽기 결과·미수행 항목 |
| `replacements/`, `previews/`, `masks/` | 실제 수정한 PZZ/GIM/PNG와 명시한 보호·편집 마스크, 수정 전후 비교. 조사만 했다면 생략 사유 |

각 교체 파일에는 **원판의 동일 멤버 해시와 수정 전 038 멤버 해시를 모두** 붙인다. 같은 PZZ를 여러 그림이 공유하면 최종 PZZ 하나로 병합한 결과를 제출하고 기존 편집이 유지됨을 확인한다. 그림이 한글이라는 미리보기만으로 게임에서 소비되는 GIM/PZZ의 검증을 대체하지 않는다.

완료는 조사 배치의 모든 그림을 개별 분류하고, 확인한 수정 대상의 실제 출력·입력 바인딩·정적 검증·재현 절차를 제출한 상태다. 전체 게임·NEXT PLUS 완료나 프리징 해결을 선언하지 않는다. 감독 AI는 입력 일치, 변경 범위, 현재 한글·로고·폰트·숫자·포인터 보호를 독립 검사한 뒤 통합 여부를 결정한다.
