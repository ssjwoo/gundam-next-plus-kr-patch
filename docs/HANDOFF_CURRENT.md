# 현재 체크포인트 — 2026-10-03

새 세션에서 한도가 재시작되어 작업을 이어가는 중입니다. 5시간 한도 잔여 30% 이하에서 새 배치를 중단하고 검증·인계를 마칩니다. 현재 후보는 018이며 전체 NEXT PLUS 완료 판정은 아직 없습니다.

- 로컬 ISO: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_018.iso`
- SHA-256: `37a05330e94abd0db58b0378904903bdb28167d33281b148f4efc0b833117510`; CRC32 `4224323C`.
- 원본 기반 xdelta: 6,844,951바이트; SHA-256 `80e6c7857d97ab12a02f3a1cdc7ec64047f2ad67dab65a79fcf8ac14871a28dc`; 재적용 결과 ISO와 동일.
- 463멤버·637개 수정 이미지 면·1,807개 요소(한국어 1,805개, 영문 NEXT 2개). 실제 ISO 읽기와 구조 검사 PASS. 실행 NOT_TESTED.
- 카드 로고 MB72/ML70, 확인한 일본어 카드 142개·212영역 전부 반영. 뉴 건담·윙 제로·에피온의 제외 사유를 해결.
- 편집 질문 4개: 정확한 앞부분 4셀과 공유 어미 1셀로 교체. 이전 전체 문장/불러오기 라벨 2개 폐기, 영역 수 순증 3.
- 해금 화면 10장·32영역 반영. MS6은 배경 로고 층/이름 패널 재구성, 코스4는 원본 장면 보존. 전체 원본 배경/모델 동일 주장이 아니라 명시한 보호 영역 검사이다.

## 다음 작업

`work/next_plus_graphics_2026-10-02/ui_consumer_audit_018/`에서 15개 공통 UI의 실제 PMF2 UV 조각을 원본/현재 후보로 비교한다. 그대로 남은 일본어, 비용 횟수·속성·획득 표시와 분할 조각의 가독성을 수동으로 판독하고 원본 소비자에 연결한 뒤 편집한다. 큼직한 아틀라스 문구가 한글이어도 실제 조각 조합이 잘릴 수 있다.

NEXT PLUS의 실제 리소스·상태·변형 분모를 닫아야 한다. 해금 화면의 모드 공유 관계는 미확정이며 AFS 숫자와 코드 상수의 일치만으로 호출을 증명할 수 없다. 가족 대표 이미지나 파일 이름으로 모드 범위를 단정하지 않는다.

## 로컬 재현 자료

`work/next_plus_graphics_2026-10-02/merged_pzz_018`, `extraction_manifest_018.json`, `expected_surfaces_018.json`, `visual_review_018.json`, `final_iso_readback_018.json`; `build/graphics_revision_2026-10-02/xdelta_roundtrip_018.json`.
편집 질문: `editor_prompt_fragments_v1`; 마지막 카드3: `card_logo_ml_batch_report_last3_v14.json`; 해금10: `unlock_v6`, `unlock_packed_v6/report.json`.
기존 후보와 원본은 덮어쓰지 않는다. 항상 텍스트 002 기준으로 새 ISO를 만들고 전체 수정 면과 원본 기반 xdelta를 검증한다.

## 공개와 실행 경계

현재 공개 릴리스는 dev-2026-09-26 그대로다. 소스·한국어 초안·집계·인계만 GitHub에 올린다. ISO·PZZ·GIM·PNG·PGF·일본어 전사·차분 파일은 커밋하지 않는다. 이전 사용자 수용을 새 후보 실행 PASS로 옮기지 않고, 종료된 게임/CMD 검증을 다시 요청하거나 실행하지 않는다.
