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
