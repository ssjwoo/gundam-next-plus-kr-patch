# 기동전사 건담 VS. 건담 NEXT PLUS 한글화 연구

PSP 일본판 **『기동전사 건담: 건담 VS. 건담 NEXT PLUS』**의 한글화를 위한 역공학·빌드 도구와 번역 초안을 공개합니다.

> [!WARNING]
> 아직 개발 중인 초안입니다. 완성된 한글 패치나 배포 가능한 릴리스가 아닙니다.

## 저작권 및 배포 방침

이 저장소는 게임 ISO, 복호화한 EBOOT, 패치된 ISO, 게임에서 추출한 이미지·폰트·음원, PPSSPP 바이너리를 포함하지 않습니다. 사용자가 합법적으로 소유한 일본판 ISO를 직접 제공해야 합니다.

지원 원본 프로필:

- 크기: `1,757,806,592` 바이트
- SHA-256: `A00C38959D52377B65F9AFB5223E02C4AC5A876B8A33C998A7FE3F07DBF1FEB3`
- 타이틀 ID: `NPJH50107`

자세한 공개 경계는 [docs/PUBLICATION_POLICY.md](docs/PUBLICATION_POLICY.md)를 보세요.

## 배포 패치 (2026-09-26)

원본 일본판 ISO에 적용하는 차분 패치를 개발 릴리스로 공개합니다.
게임 원본 데이터와 소니 폰트는 들어 있지 않습니다. 폰트는 자유 라이선스 폰트에서
새로 구운 것이라 ISO 안에 들어 있습니다.

```
xdelta3 -d -s original_jp.iso next_plus_development_v19_2026-09-26.xdelta out.iso
```

폰트는 ISO 안 `/PSP_GAME/SYSDIR/UPDATE/DATA.BIN`에 있고 게임이 `disc0:`로 읽습니다.
이번 릴리스부터 **사용자가 자기 PSP에서 폰트를 뽑을 필요가 없습니다.**

자세한 내용과 확인된 동작, 남은 작업은 `docs/RELEASE_2026-09-26.md`를 보세요.

## 현재 상태

- EBOOT 문자열 후보: 7,283개
- 한글 번역 초안: 4,271개 (독립 승인 0개)
- 독립 검수 완료: 0개
- 남은 행: 3,012개 (바이트 잡음 2,958 / 슬롯 초과 41 / 코덱 거부 12 / 게임이 직접 채우는 표 1)
- 직접 포인터 필드 정적 검증: 2,676개 (최신 개발 빌드)
- 넥스트 플러스 미션 레코드: 274개 구조 검증, 한글 초안 271개, 삽입·포인터 재검증 271개. 이 중 66개는 기존 워크북에 없던 시작점
- 넥스트 플러스 지도·설명: 99개 초안, 자동 적용 대상 98개
- PZZ: 2,125/2,125 구조 파싱 성공
- GIM 그래픽 표면: 4,272개
- PPSSPP에서 한글 폰트·커스텀 인코딩 출력 성공

최신 로컬 개발 ISO는 v19(ISO SHA-256 `a7118fce947fa72db5bd3e52fcf4f8fd397acaaa01468c9bc2a0548ed4ba789a`)입니다. PPSSPP에서 게임의 실제 libfont가 우리 폰트를 `break` 0회로 받아들이고, 메뉴 설명 패널·자동저장 안내문·미션 화면 문자열이 한국어로 그려지는 것을 확인했습니다. 실기 PSP는 아직 검수하지 않았습니다. 이 ISO와 xdelta는 저장소에 포함하지 않으며 릴리스 자산으로만 배포합니다. 이미지 글자는 후속 작업입니다.

정확한 현황은 [reports/status.json](reports/status.json), 구조 조사 결과는 [docs/RESEARCH_NOTES.md](docs/RESEARCH_NOTES.md)에 정리했습니다.

## 핵심 방식

- 폰트: 자유 라이선스 폰트(NanumGothic — NAVER, Noto Sans JP — Google. 둘 다 OFL 1.1)에서 구운 PGF. ISO에 내장되어 있고 게임이 `disc0:`로 읽는다.
- ASCII: 1바이트 그대로 사용. 숫자·영문·구두점이 정상 출력된다.
- 표기 정책(2026-09-26): 영어는 영문 그대로, 한자·일본어만 한국어로. 숫자는 ASCII 숫자로 적는다(한글 수사 우회는 되돌렸다).
- 한글 U+AC00..U+D7A3: 전용 2바이트 인코딩
  - `lead = 0x80 + ((codepoint - 0xAC00) >> 7)`
  - `trail = 0x80 + ((codepoint - 0xAC00) & 0x7F)`
- 게임의 `0xF0..0xFF` 1바이트 컨트롤 토큰을 피하기 위해 리드 바이트 범위를 제한
- 현재는 고정 슬롯 삽입만 허용하며 용량 초과 시 빌드 중단
- 문자열 길이가 허용 범위안이면 포인터 대상 주소는 변경하지 않음

## 환경

- Python 3.11 이상
- [hanpatch](https://github.com/yazzang-homelab/hanpatch)
- [PPSSPP](https://www.ppsspp.org/) 디버거 기능

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
git clone https://github.com/yazzang-homelab/hanpatch.git ..\hanpatch
pip install -e ..\hanpatch
```

## 주요 도구

- `inventory_eboot_text.py`: EBOOT CP932 문자열·직접 포인터 조사
- `apply_curated_translations.py`: 소스 일치·컨트롤 태그·슬롯 용량 검사
- `build_korean_eboot.py`: 폰트 언어·디코더·문자열을 하나의 쓰기 계획으로 구축
- `inspect_isos.py`: ISO9660 파일 구성·LBA·해시 비교
- `unpack_pzz.py`, `repack_pzz.py`: PZZ 분해·고정 할당 재패킹
- `inspect_gim.py`, `replace_gim_picture.py`: GIM 팔레트 보존 분석·교체
- `ppsspp_*.py`: PPSSPP WebSocket 디버거 자동화
- `prepare_ai_translation_handoff.py`, `validate_ai_translation_response.py`: 로컬 원문 인계·응답 검증
- `parse_next_plus_mission_records.py`, `validate_next_plus_mission_response.py`: 넥스트 플러스 미션 포인터 체인 추출·번역 응답 검사

## 번역 데이터

`translations/development_draft_2026-09-24_ko_only.jsonl`에는 ID와 한글 초안만 1,543건 수록했습니다. 일본어 원문·원시 바이트·포인터·로컬 작업용 전체 워크북은 공개하지 않습니다. 기존 `curated_batch_*.json`은 초기 초안 기록입니다. 모두 `approved`가 아니며 릴리스 품질이나 바로 적용 가능한 패치 입력을 의미하지 않습니다.

넥스트 플러스 미션 274건의 원문 인계 패키지는 저작권이 있는 원문·원시 바이트를 포함하므로 로컬에만 둡니다. 공개 저장소에는 재추출·검증 도구와 구조·진행 현황만 올립니다.

## 상표·권리

건담 및 관련 이름·자료의 권리는 각 권리자에게 있습니다. 이 프로젝트는 비공식 팬 연구이며 제작사·배급사와 무관합니다.
