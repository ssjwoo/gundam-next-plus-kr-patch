# 기동전사 건담 VS. 건담 NEXT PLUS 한글화 연구

PSP 일본판 **『기동전사 건담: 건담 VS. 건담 NEXT PLUS』**의 한글화를 위한 역공학·빌드 도구와 번역 초안을 공개합니다.

> [!WARNING]
> 아직 개발 중인 PoC입니다. 완성된 한글 패치나 배포 가능한 릴리스가 아닙니다.

## 저작권 및 배포 방침

이 저장소는 게임 ISO, 복호화한 EBOOT, 패치된 ISO, 게임에서 추출한 이미지·폰트·음원, PPSSPP 바이너리를 포함하지 않습니다. 사용자가 합법적으로 소유한 일본판 ISO를 직접 제공해야 합니다.

지원 원본 프로필:

- 크기: `1,757,806,592` 바이트
- SHA-256: `A00C38959D52377B65F9AFB5223E02C4AC5A876B8A33C998A7FE3F07DBF1FEB3`
- 타이틀 ID: `NPJH50107`

자세한 공개 경계는 [docs/PUBLICATION_POLICY.md](docs/PUBLICATION_POLICY.md)를 보세요.

## 현재 상태

- EBOOT 문자열 후보: 7,283개
- 한글 번역 초안: 120개
- 독립 검수 완료: 0개
- 미해결: 7,163개
- 직접 포인터 필드 정적 검증: 140개
- PZZ: 2,125/2,125 구조 파싱 성공
- GIM 그래픽 표면: 4,272개
- PPSSPP에서 한글 폰트·커스텀 인코딩 출력 성공

실행 검증된 최신 프로토타입은 이름 입력 안내와 이름 미입력 오류를 한글로 출력합니다. CP932 `81 A5` 진행 화살표와 커스텀 한글 인코딩의 충돌은 아직 실험 상태입니다.

정확한 현황은 [reports/status.json](reports/status.json), 구조 조사 결과는 [docs/RESEARCH_NOTES.md](docs/RESEARCH_NOTES.md)에 정리했습니다.

## 핵심 방식

- 폰트: PSP 한국어 펌웨어 PGF (`kr0.pgf`)
- ASCII: 1바이트 그대로 사용
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

## 번역 데이터

`translations/` 안의 JSON은 현재까지 선별한 번역 초안입니다. `approved`가 아니며 리리스 품질을 의미하지 않습니다.

## 상표·권리

건담 및 관련 이름·자료의 권리는 각 권리자에게 있습니다. 이 프로젝트는 비공식 팬 연구이며 제작사·배급사와 무관합니다.

