# 현재 인계 — 2026-10-06

최신 038 기준 문서를 통합하고, 사용자 요청으로 웹 AI에 전달할 잔여 이미지 검수·번역 임무와 첨부 두 개를 준비했다. 새 ISO·패치를 만들거나 게임을 실행하지 않았다. 날짜별 과거 인계는 [통합 변경 이력](../docs/HISTORY.md)에 모았다.

## 작업 기준

| 항목 | 현재 값 |
|---|---|
| 최신 작업·배포 | 038 개발판, xdelta 게시·공개 다운로드 확인 PASS |
| 마지막 사용자 수용 | 023; 요청 수정 및 이전 타이거바움 프리징 해결 확인 |
| 038 정적 검사 | PASS; 원판 기반 xdelta 재적용 PASS |
| 038 게임 실행 | NOT_TESTED; 백식 프리징 해결 미확인 |
| 전체 게임·NEXT PLUS 완료 | 판정 없음; 소비 경로·전수 범위 조사 남음 |

원판은 `Kidou Senshi Gundam - Gundam vs. Gundam Next Plus (Japan, Asia).iso`, SHA-256 `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3`, 1,757,806,592바이트다. **사용자가 제공한 `original_jp_.iso`는 패치된 입력이며 원판이 아니다.** 원판·사용자 입력은 수정하지 않는다.

최신 로컬 ISO: `build/graphics_revision_2026-10-05/next_plus_graphics_revision_038.iso`.
SHA-256 `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2`, CRC32 `EA404316`.
같은 폴더의 `next_plus_graphics_revision_038.xdelta`: 15,156,246바이트, SHA-256 `8c9677e709d49883f20c6ea9bc43f1f6b714aa3a34f3140a22abfc7914f4b3ea`, CRC32 `80FAB14B`.

수용된 023 ISO: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_023.iso`, SHA-256 `32c478704451997d7b3d8aa8ee565b2598fc84dcfe5917aad2710fa3a3b5293e`.
위 해시는 기존 검증 기록을 재사용하며 이번 문서 작업에서 대용량 ISO를 다시 해시하지 않았다. [설치·릴리스](../docs/INSTALL.md).

## 열린 문제와 증거

027의 NEXT PLUS 중급 트라이얼 마지막 **백식 호위 임무**에서 랜덤 전투 프리징이 사용자 보고됐다. 팀은 뉴 건담/아무로와 사자비/샤아. 이슈는 `OPEN / USER_REPORTED_FAIL`, 수정 결함과의 직접 연결은 `UNCONFIRMED_RUNTIME_LINK`다. 이전 타이거바움 해결 판정을 다시 열거나 현재 문제의 해결로 옮기지 않는다.

038에 비텍스트 39곳 복원, 제어 구두점 3곳, 달성 조건 47개·선택 안내 2개, 전체 대사 176개 및 이미지 3면·36문구를 반영했다. 실제 원문 경계와 포인터를 근거로 현재 슬롯 3,953개를 읽기 확인했다. [변경 상세](../docs/HISTORY.md#revision-038), [현재 문제](../docs/MISSION_FREEZE_027_2026-10-05.md).

실제 격리 수치 소비 증거는 최초 2곳에 한정하며 나머지는 원본 구조로 복원했다. 문장 중간을 읽은 6개 코덱 경고·스캐너 별칭·`unowned` 분류를 확정 손상으로 취급하지 않는다. 비정렬 대사 176개는 포인터가 가리키는 전체 문자열 기준으로 수정·검사했다. 현재 공개 카탈로그와 원판 소유권 검사를 함께 사용한다.

## 다음 AI 작업·로컬 재개

사용자가 웹 AI를 이미지 판독·번역·검수 담당으로, 현재 AI를 **실제 편집·독립 검수·통합·최종 감독 담당**으로 지정했다. [웹 AI 임무](../docs/AI_WORKER_TASK.md)를 전달한다. 첨부 두 개는 로컬 `work/ai_worker_handoff_2026-10-06/web/WEB_AI_HANDOFF.txt`와 `IMAGE_REVIEW_BATCH_001.pdf`다. ZIP·로컬 프로젝트 접근은 요구하지 않는다. 담당 AI 실행·반환 결과는 아직 없다.

첫 묶음은 원판/실제 038의 PZZ 12개·그림 50개를 비교하는 조사 배치다. AFS 인덱스·이름·크기와 PZZ 검사값을 확인한 뒤 렌더링했으며 확정 미번역 목록이나 전체 게임은 아니다. 사용 모드는 미확정이다. 웹 AI는 그림 ID별 분류·원문 판독·한국어·대략 영역을 JSON으로 반환한다. 감독 AI는 실제 입력 해시·번역·영역·모드 관계를 대조하고 확인한 항목만 편집·주입·검증한다. 038과 열린 백식 프리징 이슈를 보존하며 대표 이미지·PZZ 수만으로 완료를 선언하지 않는다.

- 상태: 로컬 `PROJECT_STATE.json`, `work/resume_2026-10-02/state.json`, `work/remaining_2026-10-05/checkpoint.json`.
- 최신 근거: [개발 검사](../reports/development_038_2026-10-05.json), [현재 슬롯](../reports/current_text_readback_2026-10-05.json), [이미지 범위](../reports/graphics_scope_2026-10-05.json), [게시 기록](../reports/release_038_2026-10-05.json).
- 재현 입력: `work/remaining_2026-10-05`의 소유권·비텍스트 복원 계획, `canonical_text_slots_038.private.json`, `canonical_text_audit.private.json` 및 038 manifest. 공개 한국어 카탈로그는 `translations/current_bound_text_ko_2026-10-05.json`.
- 그래픽 입력: `work/remaining_2026-10-04/checkpoint.json`의 확정 배치와 최신 vsel01 계획. 수용 023에 027의 모든 최종 배치·038 추가분을 유지하며 과거 텍스트 002로 되돌리지 않는다.

이전 날짜의 `checkpoint_final.py`, `checkpoint_progress.py`, `finalize_public.py`, `closing_record.py`, `update_checkpoint.py`를 무작정 재실행하지 않는다. 옛 문서 구조·후보·게시 필드를 덮을 수 있다. 현재 인계는 이 파일 하나이며 `docs/HANDOFF_CURRENT.md`는 연결 안내다.

## 유지할 사용자 지시

인게임 검수는 사용자가 맡는다. AI는 게임·에뮬레이터·종료한 CMD를 실행하거나 추가 검수를 반복 요구하지 않는다. 메인 화면·NEXT PLUS 이미지가 우선이며 모든 건담 타이틀 로고는 원본을 유지한다. 일반 UI·기체·파일럿명은 한글화 대상이다.

불필요한 중간 산출물은 검증 후 정리한다. 원판·사용자 입력·023·027·비교용 033·현재 038 및 재현 입력·검증 기록은 보존한다. [정리 기록](../reports/cleanup_2026-10-05.json). 새 한글화 작업의 5시간 한도는 **잔여 30%에서 인계**한다. 이전 세션의 잔여 관측값을 현재 사용량으로 재사용하지 않는다.
