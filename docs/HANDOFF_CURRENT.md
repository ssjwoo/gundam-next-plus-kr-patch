# 현재 인계 — 2026-10-03 진행 중

첫 메인 화면과 NEXT PLUS 모드의 모든 이미지 한글화가 최우선이며 이미지 편집·ISO 반영·GitHub 최신화는 승인됐습니다.
이번 세션 기준은 5시간 한도 잔여 **30% 이하**에서 새 묶음을 시작하지 않고 검증·GitHub·인계를 마무리하는 것입니다. 마지막 관측은 사용 50% / 잔여 50%입니다.

현재 검증 후보: `build/graphics_revision_2026-10-02/next_plus_graphics_revision_015.iso`.
SHA-256 `6e2feaf9166209ff4fe79142e92e778a24e5d5ded38e5ff2b316168cc33f65bc`, CRC32 `4B5130CA`.
453멤버·624면·1,560요소. 실제 ISO 읽기와 원본 기반 xdelta 재적용 PASS. 실행 NOT_TESTED, 사용자 수용 전이며 전체 모드 완료는 아닙니다.

깨끗한 빌드 기준은 `build/catalog_revision_2026-10-02/next_plus_catalog_revision_002.iso`, SHA-256 `d5849dd35a5a6a0d8c3ab42787660976d4a6a4b28b8f9c067d66611fe05734bb`입니다. 011 등 이전 후보는 보존하며 원본 대용으로 빌드하지 않습니다. 3,930개 연결 슬롯·미션 274개·필수 폰트 962코드를 유지합니다. 숫자 수정의 사용자 수용과 종료된 추가 CMD 검증은 그대로 유지합니다.

로컬 재개 폴더: `work/next_plus_graphics_2026-10-02/`.

- `merged_pzz_015/`, `extraction_manifest_015.json`, `expected_surfaces_015.json`, `final_iso_readback_015.json`: 최신 조합·원본·읽기·마스크.
- `series_labels_catalog_snapshot_012.json`, `series_labels_final_report_012.json`, `series_labels_batch_report_v13.json`: 작품 로고 16종·42영역. 수정된 04/07/08의 최신 읽기는 아래 알파 수정 영수증을 사용합니다.
- `alpha_quantization_audit_011.json`, `alpha_repair_report_v1.json`: 615면 대조, 43면/49,197픽셀 수정. 도구의 premultiplied alpha 비교로 투명 RGB 차이로 생기던 회색 배경을 제거했습니다.
- `series_all_consumer_013/`: 최종 조합의 작품 로고 18개 평면 미리보기. source population 18 중 일본어 16, 영문-only `stitle09/11` 보존. 이전 stitle09 일본어 판독은 폐기합니다.
- `rebuild_series_glow.py`: 불변 PMF2 전경 XY를 배경 UV 삼각형으로 재투영해 광택 생성. 전경 UV와 외부 픽셀 보호, 메시·팔레트·할당 그대로.
- `bank_mesh_inventory.json`, `bank_consumer_source_manifest.json`, `read_pmf2_meshes.py`: trl01 작품 객체 17개, trl02 18개. 이름별 원본 그림을 검토했으며 번호만으로 의미를 연결하지 않습니다.
- `review_sheets/sel_series_grid_source.png`: sel00 picture 4는 42×21 셀 3열×6행. 원본 셀 18개를 개별 확인한 자료.

현재 다음 작업:

1. 작은 공유 작품 뱅크 48개는 v4로 반영 완료. `series_bank_batch_report_v4.json`, `series_bank_catalog_private_v4.json`, `bank_english_identity_v4.json`을 사용합니다. 영문 이웃의 샘플 영역과 공유 UV를 보호했고 실제 ISO 재추출·원본 xdelta 재적용 PASS입니다.
2. brfmb 79·brfml 75의 picture 1 배경에 합쳐진 작은 작품 로고. brfml 파일명은 `brfml000`, `brfml010` 등 세 자리이며 brfmb와 번호를 임의 연결하지 않습니다. 배경/기체 그림 보호 마스크와 모든 변형 검토가 필요합니다.
3. 미확인 공통 표시, newget/그림 변형 전수 및 NEXT PLUS 소비자 목록의 범위 확인. 대표 이미지 한 장으로 가족 전체 완료를 주장하지 않습니다.

평면 미리보기는 장면 행렬·애니메이션·GE 전체 상태를 재현하지 않는 정적 자료입니다. 게임을 자체 실행하지 않으며 추가 CMD 게임 검증을 재요청하지 않습니다. 공개에는 한국어 카탈로그·코드·집계만 반영하고 원본 ISO/PNG/PZZ/GIM/PGF/일본어 전사/차분은 로컬에 둡니다. 전체 이미지/실행 품질 검증 완료로 승격하지 않습니다.

카드 원본 154개는 `card_background_logo_inventory.json`과 source 01~07 시트로 모두 검토했습니다. `card_background_logo_classification_v1.json`의 개별 판독과 해시를 연결하며, 이름/번호만으로 작품을 추정하지 않습니다. 새 로고를 편집할 때 현재 merged 014의 카드 이름 변경과 다른 GIM picture를 유지해야 합니다.

015는 세로형 카드 72개의 작은 로고 142영역(v6)을 반영했습니다. `card_logo_mb_batch_report_v6.json`의 새 로고 라벨과 결합 마스크를 사용합니다. F91/V2/Ez8의 기존 영문 기체명은 보존했으며 이 세 picture 1이 새 수정 면입니다. 총 453멤버·624면·1702요소. 실제 ISO 읽기와 xdelta 원본 왕복 PASS.

가로형 70개는 아직 통합하지 않았습니다. `card_ml_clearance_private_v8.json`에 개별 원본 해시와 기체 경계를 지정했고 `render_card_ml_v9.py`는 작은 한글 제목을 보이는 배경 칸에 배치하는 초안입니다. v1~v8의 잔여 일본어·모델 분리 오류·번짐 결과는 제외합니다. 다음 세션도 이 가로형 검토와 미확인 공통 표시·전체 변형/소비자 확인을 계속합니다.
