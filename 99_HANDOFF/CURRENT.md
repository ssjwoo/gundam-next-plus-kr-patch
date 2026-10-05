<!-- remaining-2026-10-05:start -->
# 현재 작업 — 2026-10-05 / 038 로컬 후보

027 중급 트라이얼 마지막 백식 호위 임무의 전투 중 랜덤 프리징은 USER_REPORTED_FAIL / OPEN. 사용 팀: 뉴 건담·아무로, 사자비·샤아. 직접 원인 연결 UNCONFIRMED_RUNTIME_LINK. 과거 023 타이거바움 사용자 해결 확인은 별도 범위로 보존.

최신 로컬 후보 038: ISO SHA-256 `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2`, CRC32 `EA404316`. 게임 실행 NOT_TESTED, 새 릴리스 미게시. 원판 기반 xdelta 재적용: PASS. 근거 reports/development_038_2026-10-05.json. 원판은 a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3. 사용자 original_jp_.iso는 패치된 입력이며 원판으로 사용하지 않는다.

원본 바이트로 비텍스트 39곳 복원: 수치/벡터 20곳, 내장 PNG 압축 데이터 1곳, 달성 조건 포인터 18개. 내장 PNG 3개 디코딩, 달성 조건 포인터 49개 및 원본 목록 포인터 5,682개 원판 일치. 실제 분리 수치 소비 증거는 최초 2곳에 한정. 나머지 수치는 원본 구조로 분류했고 게임플레이 경로 연결은 미확인.

문구 수정: 도입된 ASCII `~` 오류 3곳, 달성 조건 47개, 선택 안내 2개. 원문 소유권·실제 ELF로 3,953개 슬롯 검사 PASS. 비정렬 조각 중 176개는 원본 CP932 앞부분+한글 뒤쪽 혼합이었음을 확인하고 포인터가 가리키는 전체 대사로 수정했다. 176개 모두 기존 전체 문자열이 호스트 코덱에서 거부됐고 현재 전체 읽기가 통과했다. 공개 카탈로그 계획 재현과 전체 문장 소유권 보호 검사 4개 PASS. 남은 한 비정렬 행은 선택 안내 앞 스칼라의 마지막 바이트를 포함한 스캐너 별칭이며 전체 게임 완료 증거가 아니다. supplementary_slots.private.json의 6개 잘못된 코덱 경고는 전체 문장 중간을 시작점으로 읽은 결과이며 확인한 6개 전체 문장은 정상 디코딩된다. source_population_audit.private.json의 unowned는 손상 판정이 아니다.

프리 배틀 작품·스테이지 목록/선택 안내 3면·36문구 반영. vsel01 네이티브 5개 그림 재읽기, 기존 picture 0/1 및 원본 로고 193면 보호 PASS. 전체 게임/NEXT PLUS 완료 판정 없음. 사용자 인게임 검수 담당, AI 게임·에뮬레이터·CMD 실행 없음.

028~037 중간 후보는 최신 권장 아님. 비교용 033과 최신 038, 원판·사용자 입력·수용 023·공개 027 보존. 정리 근거 reports/cleanup_2026-10-05.json. 기존 027 릴리스 자산을 교체하지 않았으며 알려진 실패 알림만 갱신.

5시간 잔여 30% 관측 (2026-10-05T13:22:59.122914+00:00); 잔여 30%에서 신규 작업 종료 후 인계. 최종 인계 때 새로 관측한다.

다음 AI 작업: Audit remaining image families and actual mode consumers using the existing AFS inventory and source review records; preserve 038 and the open user-reported mission freeze.
work/remaining_2026-10-05/checkpoint_final.py 사용. checkpoint_progress.py 및 이전 날짜 finalize_public/closing_record/update_checkpoint는 오래된 후보로 덮으므로 실행 금지.
<!-- remaining-2026-10-05:end -->

<!-- remaining-2026-10-04:start -->
# 현재 작업 — 2026-10-04 남은 한글화

사용자가 인게임 검수를 맡고 누락을 나중에 보고한다. AI는 게임·에뮬레이터·종료한 CMD를 실행하거나 추가 검수를 요구하지 않는다. **이번 5시간 한도는 잔여 30%에서 인계**하며 기존 10% 지시를 대체한다. 마지막 관측: 사용 70% / 잔여 30%, 2026-10-04 09:59:25 UTC.

수용된 공개 기준은 023이며 사용자 확인으로 기존 미션 프리징은 해결됐다. 이 판정은 새 추가분의 실행 확인과 구분한다.

최신 공개 개발 후보 **027**: 추가 이미지 272면 / 255개 PZZ / 글자 1174항목, ELF data 텍스트 13곳. ISO SHA-256: 2c58ba6fc1d06cb2c4c3bfbbe16e230281accff972a7f308ecd2938a45d64cb8. 폰트·실행 코드·문자 분류표·보호된 다른 ISO 바이트 보존을 확인했다. 새 후보의 실행 결과는 NOT_TESTED다.

기본 추가분은 조작 안내 66장, 갤러리 이름 74장, 전투 이름 88장, 갤러리 UI 2면, 해금 중복 6면, 일반 크레딧 5면, 갤러리 문구 2면이다. 025 추가분은 전투 시작 대상 카드 9장, 아케이드·프리 배틀 설정 1면, 표적 격파 안내 1면, 별도 엔딩 문구 2면이다. 원본 ???와 시리즈 타이틀 로고를 유지한다.

026 추가분은 결과·기체 선택·상세 설정·곡 이름 9면이다. 027은 프리 배틀 기체 이름 66개와 출격 중지·자동 선택 슬롯을 7개 아틀라스에 추가했다. vsel01 picture 2의 작품·스테이지 목록과 picture 3/4의 작은 선택 안내는 남아 있다.

원본 기반 xdelta 왕복: **PASS**. 사용자의 직접 요청으로 [027 개발 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-04-graphics-027)를 공개했다. 공개 xdelta 15,161,344바이트·SHA-256 f1945f0a180b9dac9d19ce45114eef58592b59b0f6907090dd85de0ba6684094를 실제 다운로드와 대조해 PASS를 확인했다. 027 실행 결과는 NOT_TESTED이며 사용자 수용 기준은 023이다. 전체 텍스트·이미지·NEXT PLUS 완료를 주장하지 않는다.

재현·인계: work/remaining_2026-10-04/checkpoint.json, merged_report_027.json, 선택된 각 배치의 report/rules/source PNG/고정 할당 PZZ, text_data_plan_v1.private.json. 미확인 이미지 계열, 실제 모드 소비 경로, 기존 카탈로그 불일치 ID는 열린 항목이다.

다음 AI 작업: Extend results_v2 for vsel01 picture 2 series/stage names and pictures 3/4 selector captions using exact UV cells; retain pictures 0/1 and every selected 027 batch. Build from accepted 023 with all final replacements; continue source-bound text recovery and user runtime reports.

게시 근거: reports/release_027_2026-10-04.json, docs/RELEASE_2026-10-04_027.md. 릴리스 코드 커밋 7afae02fa3a9c1b14e0e066ea3132f47e8b74482. 기존 릴리스와 수용 기준 023을 보존했다. 로컬 finalize_public.py / closing_record.py / update_checkpoint.py는 게시 전 필드를 다시 쓸 수 있으므로 재사용 시 027 게시 근거를 병합한다. 새 이미지 작업은 시작하지 않았다.
<!-- remaining-2026-10-04:end -->

## 이전 체크포인트 — 기록 보존

# 현재 체크포인트 — 023 사용자 확인·릴리스 공개

사용자가 요청한 수정이 모두 반영됐고 미션 중 프리징도 해결됐다고 확인했다. 대화의 최신 후보 023에 대한 `USER_REPORTED_PASS`와 수정 수용을 기록했고 `NEXT_PLUS_MISSION_FREEZE_021`은 `RESOLVED_USER_REPORTED`로 닫았다. 현재 확인에서 기기별 결과·반복 횟수·파일명/해시는 별도로 제공되지 않았다. 기존 시험 요청은 종료하며 재확인을 반복 요구하지 않는다.

최신 공개: [dev-2026-10-03-graphics-023](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-023)
유일한 자산: [next_plus_graphics_revision_023.xdelta](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/download/dev-2026-10-03-graphics-023/next_plus_graphics_revision_023.xdelta)
크기 6,915,477바이트, CRC32 `830CC058`, SHA-256 `257c8682571f868b367b09890222e42b3e66d9a74b4dd9007651e97367409554`. 실제 공개 다운로드 크기·해시 PASS. 이전 021·v19 릴리스는 보존했다.

현재 수용 기준 ISO: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_023.iso`
SHA-256 `32c478704451997d7b3d8aa8ee565b2598fc84dcfe5917aad2710fa3a3b5293e`, CRC32 `CD23BC3D`. 이후 이미지 빌드는 이 023 기준의 새 출력으로 만들어 022의 폰트 경로·문자 분류표 수정을 유지한다. 과거 텍스트 002 기준으로 돌아가면서 이 수정을 누락하지 않는다.

건담 작품·게임 타이틀 로고 168멤버·311영역은 원본 복원 상태다. 보호 로고 181면 검사 PASS. 일반 UI 한글화 450멤버·617면 유지. `pbg0ff`도 원본 유지다. 전체 NEXT PLUS 모드 상태·공유 리소스·동적 UV 분모 조사는 미완료이며 전체 번역/플레이 완료 판정은 없다.

다음 AI 작업: 023을 수용한 기준으로 보존하고 실제 NEXT PLUS 상태별 리소스 요청과 동적 UV 소비자 연결 조사를 이어간다. 타이틀 로고는 원본 유지 정책을 지킨다. 새 오류 보고가 오면 해당 정확한 빌드를 고정하여 조사한다. AI는 게임·에뮬레이터 및 종료된 CMD를 실행하지 않는다. 5시간 한도 잔여 10%에서 인계하는 지시는 유지한다.

릴리스 근거: `reports/release_023_2026-10-03.json`, `docs/RELEASE_2026-10-03_023.md`. 원본 로고·정리 근거: `reports/original_title_logos_023_2026-10-03.json`, 로컬 `work/logo_restore_023_2026-10-03` 및 023 manifest/재적용 기록. 공개한 게임 자산은 xdelta 하나이며 ISO/추출 데이터는 로컬에만 보관한다.
