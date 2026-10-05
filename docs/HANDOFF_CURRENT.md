<!-- remaining-2026-10-05:start -->
# 현재 작업 — 2026-10-05 / 038 로컬 후보

027 중급 트라이얼 마지막 백식 호위 임무의 전투 중 랜덤 프리징은 USER_REPORTED_FAIL / OPEN. 사용 팀: 뉴 건담·아무로, 사자비·샤아. 직접 원인 연결 UNCONFIRMED_RUNTIME_LINK. 과거 023 타이거바움 사용자 해결 확인은 별도 범위로 보존.

최신 로컬 후보 038: ISO SHA-256 `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2`, CRC32 `EA404316`. 게임 실행 NOT_TESTED, 새 릴리스 미게시. 원판 기반 xdelta 재적용: PASS. 근거 reports/development_038_2026-10-05.json. 원판은 a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3. 사용자 original_jp_.iso는 패치된 입력이며 원판으로 사용하지 않는다.

원본 바이트로 비텍스트 39곳 복원: 수치/벡터 20곳, 내장 PNG 압축 데이터 1곳, 달성 조건 포인터 18개. 내장 PNG 3개 디코딩, 달성 조건 포인터 49개 및 원본 목록 포인터 5,682개 원판 일치. 실제 분리 수치 소비 증거는 최초 2곳에 한정. 나머지 수치는 원본 구조로 분류했고 게임플레이 경로 연결은 미확인.

문구 수정: 도입된 ASCII `~` 오류 3곳, 달성 조건 47개, 선택 안내 2개. 원문 소유권·실제 ELF로 3,953개 슬롯 검사 PASS. 비정렬 조각 중 176개는 원본 CP932 앞부분+한글 뒤쪽 혼합이었음을 확인하고 포인터가 가리키는 전체 대사로 수정했다. 176개 모두 기존 전체 문자열이 호스트 코덱에서 거부됐고 현재 전체 읽기가 통과했다. 공개 카탈로그 계획 재현과 전체 문장 소유권 보호 검사 4개 PASS. 남은 한 비정렬 행은 선택 안내 앞 스칼라의 마지막 바이트를 포함한 스캐너 별칭이며 전체 게임 완료 증거가 아니다. supplementary_slots.private.json의 6개 잘못된 코덱 경고는 전체 문장 중간을 시작점으로 읽은 결과이며 확인한 6개 전체 문장은 정상 디코딩된다. source_population_audit.private.json의 unowned는 손상 판정이 아니다.

프리 배틀 작품·스테이지 목록/선택 안내 3면·36문구 반영. vsel01 네이티브 5개 그림 재읽기, 기존 picture 0/1 및 원본 로고 193면 보호 PASS. 전체 게임/NEXT PLUS 완료 판정 없음. 사용자 인게임 검수 담당, AI 게임·에뮬레이터·CMD 실행 없음.

028~037 중간 후보는 최신 권장 아님. 비교용 033과 최신 038, 원판·사용자 입력·수용 023·공개 027 보존. 정리 근거 reports/cleanup_2026-10-05.json. 기존 027 릴리스 자산을 교체하지 않았으며 알려진 실패 알림만 갱신.

5시간 잔여 35% 관측 (2026-10-05T13:14:34.824016+00:00); 잔여 30%에서 신규 작업 종료 후 인계. 최종 인계 때 새로 관측한다.

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

## 이전 로고 복원·프리징 재시험 대기 기록 — 역사

# 현재 체크포인트 — 023 타이틀 로고 원본 복원

사용자 요청으로 모든 건담 작품·게임 타이틀 로고를 원본 유지 대상으로 바꿨다. 복원 168멤버·311영역; 원래 유지하던 영문·추가 게임 로고를 포함한 보호 정책 181면 PASS. 메뉴·기체/파일럿명·미션 등 일반 텍스트는 한글 유지. `pbg0ff.pzz`도 번역하지 않는다. [영구 정책](GUNDAM_TITLE_LOGO_POLICY.md), [복원·검증 기록](ORIGINAL_TITLE_LOGOS_023_2026-10-03.md).

최신 로컬: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_023.iso`
SHA-256 `32c478704451997d7b3d8aa8ee565b2598fc84dcfe5917aad2710fa3a3b5293e`; CRC32 `CD23BC3D`. 원본 기반 xdelta 6,915,477바이트, SHA-256 `257c8682571f868b367b09890222e42b3e66d9a74b4dd9007651e97367409554`. ISO 읽기·로고/한글 보호 픽셀·PZZ 검사값·원본 차분 재적용 PASS. 실행 NOT_TESTED. 공개 릴리스는 021이다.

022의 EBOOT·폰트·미션은 023에서 완전히 같다. 022는 프리징 원인을 비교할 별도 기준으로 보존한다. **미션 전투 프리징은 사용자 재시험 대기이며 해결됐다고 주장하지 않는다.** 사용자 게임 관찰을 받은 뒤 같은 빌드를 보존하고 원본 비교나 오류 로그로 범위를 좁힌다. 게임·에뮬레이터 및 종료된 CMD는 AI가 실행하지 않는다.

중복 산출물 14,437파일·1.84GiB 정리 완료. 020 ISO는 삭제했으나 검증된 차분과 진단은 보존한다. 원본·사용자 자료·수용한 기준·021/022/023·현재 입력/마스크는 유지한다. 앞으로 검증이 끝난 임시 복제본은 수시로 정리하고 재적용은 중복 ISO 없이 스트림 검사한다.

다음 AI 작업: 사용자의 022 또는 023 전투 결과를 처리한다. 프리징이 계속되면 해당 파일을 고정하고 오류 원인을 더 좁힌다. 이후 일반 UI의 모드 상태·동적 UV 조사를 이어가며 로고는 원본 그대로 유지한다. 현재 5시간 한도 잔여 10%에서 인계하는 지시는 유지한다.

재현: `work/logo_restore_023_2026-10-03/restoration_plan.json` → `tools/restore_original_gim_regions.py`(중단 결과는 `--resume`로 동일성 검사) → 022 기준 `tools/build_graphics_revision_iso.py` → `verify_and_delta.py`. 기존 출력 파일을 덮어쓰지 않고 새 revision 경로로 만든다. 복원 카탈로그의 `target_ko`는 역사 필드로 옮겼으며 현재 build_action은 `preserve_original`이다.

## 이전 022 진단 및 021/020 이미지 작업 — 아래는 역사 기록

# 현재 체크포인트 — 022 미션 프리징 수정 후보

사용자가 NEXT PLUS 「타이거바움의 침입자」 전투 중 불규칙한 전체 정지를 반복 보고했다. 사진은 PSP 실기이며 원본 포인터 체인 기준 미션은 `NPMIS_0018`이다. 021 부팅 성공은 유지하되 전투 프리징은 별도 미해결 오류로 기록한다.

최신 로컬 후보: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_022.iso`
SHA-256 `1a2be2f2c01c165091afd7268186ddb329affa5014cebb365b6fa82dc0762ec7`, CRC32 `C88A9CA8`. 총 135바이트만 변경했고 EBOOT 밖의 모든 ISO 바이트와 폰트·미션·이미지는 021과 동일하다. 원본 문자 분류표 257바이트 복구, 실제 분류 함수 256입력 대조, 폰트 초기화 격리 32사례·새 폰트 빌더 회귀 PASS. ISO 읽기·원본 기반 xdelta 재적용 PASS. 실행 `NOT_TESTED`; 프리징 인과관계·해결은 미확인이다.

로컬 차분: `next_plus_graphics_revision_022.xdelta`, 6,892,596바이트, SHA-256 `41e553db27f770eedc2d48b0d61d3714e3275c5c4fbabee88b12729bab892c0b`. 중복 재적용 ISO는 생성하지 않고 출력 스트림을 해시 검증했다. 기존 021은 보존하며 022는 공개하지 않았다. 021 릴리스에 전투 프리징 경고를 추가했다.

현재 실제 의존성은 **사용자의 022 부팅·동일 미션 2~3회 끝까지 플레이 결과**다. AI는 게임·에뮬레이터 및 종료된 CMD 검증을 실행하지 않는다. 재시험을 통과해야 해당 조건에서 수정 효과를 기록하고, 계속 발생하면 같은 022를 보존한 채 원본 비교나 호환되는 에뮬레이터 오류 로그로 범위를 좁힌다. 이후에 추가 이미지 작업을 재개한다.

근거: [진단 기록](MISSION_FREEZE_021_2026-10-03.md), `reports/mission_freeze_021_2026-10-03.json`, 로컬 `work/mission_freeze_021_2026-10-03`. 공개 도구 `tools/repair_font_path_ctype.py`와 수정한 `tools/build_userfont_iso.py`는 임의의 0 구간에 경로를 배치하는 동작을 제거한다.

이번 진단 중 확인한 5시간 한도는 사용 16%·잔여 84%이며 사용자 잔여 10% 인계 기준은 유지한다. 이번 대기는 한도 종료가 아니라 새 후보의 실제 전투 관찰이 필요한 상태다.

## 021 부팅 확인과 배포 — 역사 기록

# 현재 체크포인트 — 021 사용자 부팅 확인·개발 릴리스 공개

020에서 PSP 로고 직후 첫 로딩 정지가 PSP-3000·PPSSPP 양쪽에서 보고되었다. 검사값을 수정한 021에 대해 사용자가 부팅 완료와 현재까지 정상 게임플레이를 보고해 첫 로딩 문제를 닫았다. 이번 재시험의 기기별 결과와 전체 플레이 범위는 제공되지 않았다. 사용자 한도 기준 잔여 10%에서 새 이미지 배치는 중단하며 이번 추가 지시로 릴리스 게시를 마쳤다.

021: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_021.iso`
SHA-256 `24682c836195d64903a502ee149ea1d09c1c22c18c47952dcc3fe844d8482e68`, CRC32 `255F9AD6`. 466멤버·643면 ISO 재읽기와 원본 기반 xdelta 재적용 PASS. 실행 `USER_REPORTED_PASS`는 부팅과 현재까지의 플레이에 한정한다.

466개 PZZ의 마지막 16바이트 검사값을 다시 계산했다. 본문·한글 이미지·텍스트·폰트는 020과 동일하며 원본 검사 함수 6개 사례 대조도 PASS다. `reports/boot_failure_020_2026-10-03.json`, `docs/BOOT_FAILURE_020_2026-10-03.md`, 로컬 `work/boot_failure_020_2026-10-03`에 근거를 보관했다.

최신 공개 릴리스는 [dev-2026-10-03-graphics-021](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-021)이다. 첨부 파일은 `next_plus_graphics_revision_021.xdelta` 하나이며 6,892,606바이트, SHA-256 `d32ad5e2b349b7e3c061b8982ae9df93c33fe29cfe6a4c2e807c3aba105f4879`. 공개 다운로드 해시 PASS는 `reports/release_021_2026-10-03.json`에 기록했다. [적용 안내](RELEASE_2026-10-03_021.md)를 참조하고 기존 v19는 보관한다.

다음 AI 작업: 021을 보존하고 아래 원본 `pbg0ff.pzz` 로고와 기존 한글 메인 로고의 픽셀·구성을 비교해 편집 계획을 만든 뒤, NEXT PLUS 상태별 리소스·동적 UV 연결 조사를 이어간다. 전체 NEXT PLUS 한글화 완료는 아니다. 종료된 게임/CMD 검증은 다시 실행하지 않는다.

## 이전 이미지 작업 인계 — 역사 기록

# 현재 체크포인트 — 2026-10-03

5시간 한도 사용 71%·잔여 29%를 확인해 사용자 지정 잔여 30% 기준에서 새 배치를 중단했습니다. 현재 후보 020의 검증과 GitHub 반영을 마쳤으며, 아래 발견 사항부터 다음 세션에서 이어갑니다. 전체 NEXT PLUS 완료 판정은 아직 없습니다.

- 로컬 ISO: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_020.iso`
- SHA-256: `c1b2c1d4f5d63af345c57dd0a6069e87507324f6fe188bdcaa7dd6e030213ffc`; CRC32 `86EA8C0A`.
- 원본 기반 xdelta: 6,885,921바이트; SHA-256 `a7d529b2c2f016e084ca16b81ceaa7e9d13092408c9b22cdf4f27444dd095dbf`; 재적용 결과 ISO와 동일.
- 466멤버·643개 수정 이미지 면·1,878개 요소(한국어 1,876개, 영문 NEXT 2개). 실제 ISO 읽기와 구조 검사 PASS. 실행 NOT_TESTED.
- 카드 로고 MB72/ML70, 확인한 일본어 카드 142개·212영역 전부 반영. 뉴 건담·윙 제로·에피온의 제외 사유를 해결.
- 편집 질문 4개: 정확한 앞부분 4셀과 공유 어미 1셀로 교체. 이전 전체 문장/불러오기 라벨 2개 폐기, 영역 수 순증 3.
- 해금 화면 10장·32영역 반영. MS6은 배경 로고 층/이름 패널 재구성, 코스4는 원본 장면 보존. 전체 원본 배경/모델 동일 주장이 아니라 명시한 보호 영역 검사이다.

## 다음 작업

공통 UI의 원본/현재 UV 조각 검토와 020 후속 수정은 아래 기록대로 마쳤다. 다음 작업은 원본 EBOOT와 리소스 관리 코드에서 실제 NEXT PLUS 상태별 호출, 동적 UV 덮어쓰기, 공유 해금 화면의 모드 연결을 증명하는 것이다. 분할·회전된 원본 조각은 단일 경계 상자를 전체 문장으로 간주하지 않고 전체 XY 조합으로 검토한다.

NEXT PLUS의 실제 리소스·상태·변형 분모를 닫아야 한다. 해금 화면의 모드 공유 관계는 미확정이며 AFS 숫자와 코드 상수의 일치만으로 호출을 증명할 수 없다. 가족 대표 이미지나 파일 이름으로 모드 범위를 단정하지 않는다.

우선 추가 배경 계열에서 발견한 `pbg0ff.pzz`의 일본어 게임 로고를 작업한다. 원본 PBG 계열 96멤버·96면(각 480×272)을 6개 검토 시트로 전수 관찰했고, 이 1면에서 일본어 로고를 확인했다. 나머지 95면에서는 일본어를 관찰하지 못했다. 해당 1면은 020에 아직 반영되지 않았다. 실제 NEXT PLUS 호출 관계는 미확정이므로 이 계열의 파일 수를 모드 전체 분모로 쓰지 않는다. 먼저 기존 메인 로고와 원본 픽셀·구성을 비교하고, 같다는 증거가 없으면 새 편집과 마스크를 만든다. 020은 보존하고 텍스트 002 기준의 새 후보를 만든다.

원본 이미지 위치: `work/next_plus_graphics_2026-10-02/mode_backgrounds_020/rendered/pbg0ff/part_000_picture_000.png`. 추출·렌더 manifest와 `source_review_00.png`부터 `source_review_05.png`도 같은 작업 폴더에 있다. 미완료 항목은 `mode_backgrounds_020/review_checkpoint.json`에 고정했다.

## 실제 로더 조사 체크포인트

원본 ELF의 파일 크기 표 `0x8a56160`과 AFS 2,592멤버를 비교해 모두 `표의 크기 + 16 = AFS 크기`가 일치함을 확인했다. 크기 조회 함수는 `0x8885934`이며 리소스 ID를 `0x7fff`로 마스킹한다. 비동기 요청 함수 `0x8886ea4`, 큐 함수 `0x8887008`, 아카이브 초기화 `0x8883c40`, 경로 표 `0x8a1bd2c`를 확인했다. 이는 리소스 ID와 AFS 인덱스 연결의 증거이며, 모드 상태 연결까지 증명한 것은 아니다.

코드가 실제 표를 인덱싱해 요청 함수에 넘기는 경로를 확인한 것은 해금 표 `0x8a6cd6c` → 로더 `0x8925268`(고유 11멤버), 공통 trl 표 `0x8a6cd84` → `0x8925358`(고유 5멤버), 기체 표 `0x8a6cd90` → `0x892554c`(고유 66멤버)이다. 해금 로더 호출 `0x890e6c0`·`0x890e71c`·`0x890e77c`와 trl 호출 영역 `0x8935f38`·`0x8936324`·`0x8937a80`·`0x8939554`·`0x893c5d8`부터 화면 상태와 모드 진입 경로를 연결한다. trl 객체 생성 함수는 `0x89254a8`이다.

스킬 표 `0x8a6ce84`·기체 그림 표 `0x8a6cf78`는 각 고유 66멤버지만 로더 후보 `0x892594c`·`0x8925b44`의 실제 경로는 추가 확인이 필요하다. 배경 표 후보 `0x8a6d06c`와 로더 후보 `0x8925f60`도 미확정이다. 배경 표의 97워드 임시 읽기는 뒤의 데이터까지 넘어가므로 **97개를 실제 표 길이나 자산 수로 인용하지 않는다**. 원본 파일 이름 계열의 96멤버와 표 길이는 별개다.

로컬 근거는 `resource_reachability/loader_table_checkpoint_v1.json`, `compiled_size_table_v1.json`, `resource_list_code_candidates_v1.json`에 있다. 공개 집계는 `reports/graphics_resource_scope_2026-10-03.json`이다. 원본 표·이미지·일본어 전사는 공개하지 않는다.

## 로컬 재현 자료

`work/next_plus_graphics_2026-10-02/merged_pzz_020`, `extraction_manifest_020.json`, `expected_surfaces_020.json`, `visual_review_020.json`, `final_iso_readback_020.json`; `build/graphics_revision_2026-10-02/xdelta_roundtrip_020.json`.
편집 질문: `editor_prompt_fragments_v1`; 마지막 카드3: `card_logo_ml_batch_report_last3_v14.json`; 해금10: `unlock_v6`, `unlock_packed_v6/report.json`.
기존 후보와 원본은 덮어쓰지 않는다. 항상 텍스트 002 기준으로 새 ISO를 만들고 전체 수정 면과 원본 기반 xdelta를 검증한다.

## 공개와 실행 경계

현재 공개 릴리스는 dev-2026-09-26 그대로다. 소스·한국어 초안·집계·인계만 GitHub에 올린다. ISO·PZZ·GIM·PNG·PGF·일본어 전사·차분 파일은 커밋하지 않는다. 이전 사용자 수용을 새 후보 실행 PASS로 옮기지 않고, 종료된 게임/CMD 검증을 다시 요청하거나 실행하지 않는다.

## 020 후속 체크포인트

공통 UV 수정 17개·기존 16개 폐기, 로비/통신 49개, 전투 조건 동일 원본 셀 18개, 중간 전적 1개, 작은 확인/편집 2개: 새 라벨 87개·순증 71개. `shared_ui_uv_v3`, `shared_variants_v3`, `tiny_shared_v2`를 순서대로 반영했다. 실패한 v1/v2 시제품을 사용하지 않는다. 비용의 기 접미사와 일부 공유 셀은 실제 동적 UV 연결이 미확정이다.

`ui_consumer_audit_018_v2`의 1,272개 원본/018 조각을 전수 육안 검토했다. `ui_consumer_audit_019`의 63개 변경 조각도 육안 검토했다. 작은 확인/편집 표시는 UV 크기 필터로 누락되는 원본 아틀라스에서 추가 확인했다. 새 `tools/inspect_pmf2_ui_consumers.py`는 기존 형식의 좌표·삼각형과 회귀 일치하며 법선 포함 0x142 프리미티브 23개(정점 74개)도 해독한다. 원본 효과 그림의 일본어는 관찰되지 않았다. 전체 15자산의 지원 불명 정점은 0개지만 전체 모드 소비자 관계가 증명된 것은 아니다.

수정되지 않은 핵심 자산 9개·30면도 검토해 일본어를 관찰하지 못했다. NEXT PLUS 전체 상태별 리소스 분모, 동적 UV, 실제 모드 호출 연결과 분할/회전 표시의 전체 XY 조합은 남아 있다. 종료된 게임/CMD 검증을 다시 요청하거나 실행하지 않는다.
