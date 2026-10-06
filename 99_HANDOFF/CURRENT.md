# 현재 인계 — 2026-10-06

사용자가 반환한 웹 AI 배치 001을 대조·감독 검수하고 지명 두 곳을 수정한 **039 로컬 ISO·원판용 xdelta**를 만들었다. 공개 릴리스는 038을 유지하며 게임을 실행하지 않았다. [039 변경·검증](../docs/HISTORY.md#revision-039).

## 작업 기준

| 항목 | 현재 값 |
|---|---|
| 최신 작업·배포 | 로컬 작업본 039; 공개 릴리스 038의 다운로드 확인 PASS |
| 마지막 사용자 수용 | 023; 요청 수정 및 이전 타이거바움 프리징 해결 확인 |
| 039 정적 검사 | PASS; 원판 기반 xdelta 재적용 PASS |
| 039 게임 실행 | NOT_TESTED; 백식 프리징 해결 미확인 |
| 전체 게임·NEXT PLUS 완료 | 판정 없음; 소비 경로·전수 범위 조사 남음 |

원판은 `Kidou Senshi Gundam - Gundam vs. Gundam Next Plus (Japan, Asia).iso`, SHA-256 `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3`, 1,757,806,592바이트다. **사용자가 제공한 `original_jp_.iso`는 패치된 입력이며 원판이 아니다.** 원판·사용자 입력은 수정하지 않는다.

최신 로컬 ISO: `build/graphics_revision_2026-10-06/next_plus_graphics_revision_039.iso`.
SHA-256 `fa44294cc63f214f983209a95937872617d96920b942cfcd29fa9868c4e829cb`, CRC32 `6398666D`, 1,757,806,592바이트.
같은 폴더의 `next_plus_graphics_revision_039.xdelta`: 15,156,262바이트, SHA-256 `587a67695c539be3b7ba250153266d60eebd175d315e848304ee6d7116376576`, CRC32 `A56BDEB8`.

수정 기준 038은 `build/graphics_revision_2026-10-05/next_plus_graphics_revision_038.iso`, SHA-256 `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2`다. 공개 릴리스는 038이며 039는 아직 로컬에만 있다.

수용된 023 ISO: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_023.iso`, SHA-256 `32c478704451997d7b3d8aa8ee565b2598fc84dcfe5917aad2710fa3a3b5293e`.
039 해시는 이번 빌드·패치 재적용에서 실제 계산했고, 038·023 기록은 재사용한다. [설치·릴리스](../docs/INSTALL.md).

## 열린 문제와 증거

027의 NEXT PLUS 중급 트라이얼 마지막 **백식 호위 임무**에서 랜덤 전투 프리징이 사용자 보고됐다. 팀은 뉴 건담/아무로와 사자비/샤아. 이슈는 `OPEN / USER_REPORTED_FAIL`, 수정 결함과의 직접 연결은 `UNCONFIRMED_RUNTIME_LINK`다. 이전 타이거바움 해결 판정을 다시 열거나 현재 문제의 해결로 옮기지 않는다.

038에 비텍스트 39곳 복원, 제어 구두점 3곳, 달성 조건 47개·선택 안내 2개, 전체 대사 176개 및 이미지 3면·36문구를 반영했다. 실제 원문 경계와 포인터를 근거로 현재 슬롯 3,953개를 읽기 확인했다. [변경 상세](../docs/HISTORY.md#revision-038), [현재 문제](../docs/MISSION_FREEZE_027_2026-10-05.md).

실제 격리 수치 소비 증거는 최초 2곳에 한정하며 나머지는 원본 구조로 복원했다. 문장 중간을 읽은 6개 코덱 경고·스캐너 별칭·`unowned` 분류를 확정 손상으로 취급하지 않는다. 비정렬 대사 176개는 포인터가 가리키는 전체 문자열 기준으로 수정·검사했다. 현재 공개 카탈로그와 원판 소유권 검사를 함께 사용한다.

## 다음 AI 작업·로컬 재개

사용자가 웹 AI를 이미지 판독·번역·검수 담당으로, 현재 AI를 **실제 편집·독립 검수·통합·최종 감독 담당**으로 지정했다. [웹 AI 임무](../docs/AI_WORKER_TASK.md). 첫 첨부 두 개는 로컬 `work/ai_worker_handoff_2026-10-06/web/WEB_AI_HANDOFF.txt`와 `IMAGE_REVIEW_BATCH_001.pdf`이며 038에 고정된 자료다. ZIP·로컬 접근은 요구하지 않는다. 반환 파일 `E:/codex/web_ai_result_batch_001.json`을 수신했으며 SHA-256은 `39d11ced04d7bdb61ae9f197a4f0e7df2a93c85b360d1bc748e29d0a270e2fb7`다.

첫 묶음은 PZZ 12개·그림 50개의 조사 배치다. 반환한 119개 영역과 ID·좌표 범위를 대조했다. G041의 지명 두 곳을 원판에서 재확인해 **미지의 구역**, **궤도 엘리베이터 중계점**으로 고쳤다. `trl03.pzz` part 1 / picture 3의 두 영역만 편집했으며 보호 픽셀 0, 다른 그림·메시·팔레트·컨테이너·로고 193면을 검증했다. [감독 검수](../reports/web_ai_review_batch_001_2026-10-06.json).

G017의 숫자 플레이트 침범 주장은 채택하지 않았다. `ckpt00_ck065`의 두 primitive는 같은 XY를 덮고 뒤쪽 깊이 -3·회색 0.4, 앞쪽 깊이 0으로 구분된다. 정점 순서는 다르며 원판/038 메시가 같다. 이 증거는 뒤쪽 효과 레이어 해석을 뒷받침하지만 다른 행의 동적 UV·실제 실행은 미확정이다. G017-R07, G022-R10, G028-R04는 판독·기능 미확정으로 보존했다. 일반 영어를 모두 제외한다는 웹 AI 제안도 채택하지 않는다.

사용자의 대규모 배치 요청에 따라 **배치 002: 039 기준 PZZ 251개·비교 그림 422개·PDF 423쪽**을 준비했다. 첨부는 `work/ai_worker_handoff_2026-10-06/web_batch_002/WEB_AI_HANDOFF_BATCH_002.txt`와 `IMAGE_REVIEW_BATCH_002.pdf` 두 개다. 공용 UI·메뉴, 모든 trsk/trms 계열, 조작·기체별 안내, 해금 안내를 원판/실제 039에서 바인딩했다. 20개는 첫 배치 영문·판독 보류 재검토, 402개는 신규 G051–G452다. 422개가 확정 미번역 개수는 아니다. [준비·레이아웃 검증](../reports/web_ai_handoff_batch_002_2026-10-06.json). 모든 PDF 페이지를 렌더링하고 18개 전체 축소 비교표·대표 6쪽을 직접 확인했다. 이는 레이아웃 검증이며 번역 검수 완료가 아니다.

다음 AI 작업은 사용자에게서 `web_ai_result_batch_002.json`을 받아 이미지 ID·원문·기존 한글·영역을 독립 확인한 뒤 채택한 제안만 039에 반영하는 것이다. 웹 AI 자동 전달·작업 시작·결과 수신은 아직 없다. TXT는 25개씩 순서대로 검토하고 중단 시 실제 완료한 JSON·미검토 ID·다음 ID를 보존하도록 지시한다. 첫 배치의 038 자료와 혼동하지 않는다. 전체 50개를 이번 턴에 다시 심층 판독한 것은 아니며 감독 심층 검수는 G017·G041에 집중했다. 전체 완료·프리징 해결을 선언하지 않는다.

- 상태: 로컬 `PROJECT_STATE.json`, `work/resume_2026-10-02/state.json`, `work/remaining_2026-10-05/checkpoint.json`.
- 최신 근거: [039 개발 검사](../reports/development_039_2026-10-06.json), [038 현재 슬롯](../reports/current_text_readback_2026-10-05.json), [039 이미지 범위](../reports/graphics_scope_039_2026-10-06.json), [038 게시 기록](../reports/release_038_2026-10-05.json).
- 재현: `work/web_result_review_2026-10-06/receive_and_inspect.py`, `build_corrections.py` 및 원판/038 입력·글자 규칙·소스 manifest·PZZ 교체·감독 판단 기록. 기존 도구로 039 ISO·원판용 xdelta를 생성했고 `build/graphics_revision_2026-10-06/`에 manifest·재적용 결과가 있다.
- 재현 입력: `work/remaining_2026-10-05`의 소유권·비텍스트 복원 계획, `canonical_text_slots_038.private.json`, `canonical_text_audit.private.json` 및 038 manifest. 공개 한국어 카탈로그는 `translations/current_bound_text_ko_2026-10-05.json`.
- 그래픽 입력: `work/remaining_2026-10-04/checkpoint.json`의 확정 배치와 최신 vsel01 계획. 수용 023에 027의 모든 최종 배치·038 추가분을 유지하며 과거 텍스트 002로 되돌리지 않는다.

이전 날짜의 `checkpoint_final.py`, `checkpoint_progress.py`, `finalize_public.py`, `closing_record.py`, `update_checkpoint.py`를 무작정 재실행하지 않는다. 옛 문서 구조·후보·게시 필드를 덮을 수 있다. 현재 인계는 이 파일 하나이며 `docs/HANDOFF_CURRENT.md`는 연결 안내다.

## 유지할 사용자 지시

인게임 검수는 사용자가 맡는다. AI는 게임·에뮬레이터·종료한 CMD를 실행하거나 추가 검수를 반복 요구하지 않는다. 메인 화면·NEXT PLUS 이미지가 우선이며 모든 건담 타이틀 로고는 원본을 유지한다. 일반 UI·기체·파일럿명은 한글화 대상이다.

불필요한 중간 산출물은 검증 후 정리한다. 원판·사용자 입력·023·027·비교용 033·기준 038·현재 039 및 재현 입력·검증 기록은 보존한다. [정리 기록](../reports/cleanup_2026-10-05.json). 새 한글화 작업의 5시간 한도는 **잔여 30%에서 인계**한다. 이전 세션의 잔여 관측값을 현재 사용량으로 재사용하지 않는다.
