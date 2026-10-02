# 현재 인계 — 2026-10-03

첫 메인 화면과 NEXT PLUS 모드의 모든 이미지 한글화가 최우선입니다. 이미지 편집과 ISO 반영까지 승인됐습니다.
사용자 최신 기준: 5시간 한도 잔여 **10% 이하**에서 새 작업을 시작하지 않고 검증·GitHub·인계를 마무리합니다. 예전 20% 기준은 폐기했습니다.
이번 세션은 사용률 90%를 확인한 시점에 새 이미지 작업을 종료했습니다. 최종 후보 검증을 마쳤으며 다음 세션은 아래 남은 로고부터 재개합니다.

현재 후보: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_011.iso`.
SHA-256 `d3f4c6b7fcdcd96778382eb75a2f0aae03cea33d6b5f0085ae58b52e87263f1a`, CRC32 `8FDB2B3B`.
450멤버·615면, ISO 실제 읽기와 원본 기반 xdelta 재적용 PASS. 실행 NOT_TESTED.
완료 범위: [이미지 체크포인트](GRAPHICS_2026-10-03.md).

깨끗한 빌드 기준은 `build/catalog_revision_2026-10-02/next_plus_catalog_revision_002.iso`, SHA-256 `d5849dd35a5a6a0d8c3ab42787660976d4a6a4b28b8f9c067d66611fe05734bb`입니다. 이 기준으로 새 번호를 빌드하며 기존 그래픽 후보를 원본 대용으로 사용하지 않습니다.
3,930개 연결 슬롯, 미션 274개, 필수 폰트 962코드를 유지합니다. 미연결 공개 ID 162개는 남은 게임 문자열 수가 아닙니다.
기존 숫자 수정은 사용자 수용 완료이며 추가 CMD 검증은 종료됐습니다. 새 후보는 사용자 실행 수용 전입니다.

로컬 재개 폴더: `work/next_plus_graphics_2026-10-02/`.

- `merged_pzz_011/`, `extraction_manifest_011.json`, `expected_surfaces_011.json`: 현재 조합·마스크·기대 면.
- `final_iso_readback_011.json`, `build/graphics_revision_2026-10-02/xdelta_roundtrip_011.json`: 실제 ISO·재적용 영수증.
- `ui_batch_report_v8.json`, `briefing_unit_batch_report_v1.json`, `briefing_card_batch_report_v2.json`, `main_logo_report_v2.json`: 008 이후 계승한 묶음.
- `ui_batch_report_pilot_data_v3.json`, `pilot_data_selection_catalog_private.json`: 32개 통계·등급 등과 선택 이름 56조각.
- `selection_name_consumers_v3.json` 및 미리보기 3장: 실제 이름 객체 66개를 확인한 자료.
- `series_labels_final_report_011.json`, `series_labels_catalog_private.json`, `visual_review_011.json`: 작품 로고 13개·25영역, 남은 6개 목록.
- 로고 v3은 일본어 그림자 잔재가 남아 제외. 최종 v5/v6는 색상 씨앗과 13×13 확장으로 원래 외곽선을 제거하며 내부 그림 복원은 근사치입니다.
- 원본 `briefing/`은 341멤버·532면. source/consumer 미리보기는 투명 배경을 매트에 합성해 확인할 것. 원본 PNG의 RGB만 보면 알파로 숨겨진 글자를 놓칩니다.
- 009는 로고 본문 추가 전 내부 후보이며 원본 차분을 만들지 않았습니다. 전달 대상은 검증된 011입니다.
- `remaining_logo_notes_011.json`: 남은 6개 로고의 분할·광택·부제 조사 메모. 다음 첫 묶음은 `stitle0c`의 본문과 광택 대응 영역을 권장합니다.
- `series_labels_catalog_snapshot_011.json`: 현재 25영역 작성 카탈로그의 고정 사본. 후속 작성 시 이 사본과 011의 기대 이미지·마스크를 보존합니다.

다음 우선순위:

1. `stitle09/0a/0b/0c/0f/10`: 큰 일본어, UV 경계에 나뉜 조각, 광택용 중복, 작은 부제를 모두 처리. 02/08의 별도 조각은 최종 v5/v6에서 함께 제거했습니다.
2. `sel00` picture 4, `trl01` picture 2, `trl02` picture 2와 브리핑 카드 안의 작은 작품 로고. 전체 원본·변형을 확인.
3. 미확인 공통 표시와 전체 NEXT PLUS 소비자/변형 목록. `trl02` picture 0의 작은 표시 등을 원문 확인 후 처리.

기존 `ui_quad_population.json` Q 번호는 재번호화하지 않습니다. v2 목록은 RGBA4444 정점 12바이트 해석을 반영한 보완 조사입니다.
평면 미리보기는 실제 실행 검증이 아닙니다. 게임을 자체 실행하지 말고 사용자 지시를 따릅니다.
`PROJECT_STATE.json`과 `work/resume_2026-10-02/state.json`은 동일한 상태 사본입니다. 공개 카탈로그는 한국어만, approved=false를 유지하며 ISO·원본 이미지·폰트·PZZ를 커밋하지 않습니다.
