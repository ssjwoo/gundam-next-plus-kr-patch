# 기동전사 건담 VS. 건담 NEXT PLUS 한글패치

PSP 일본판 **NPJH50107**의 비공식 한글화 프로젝트입니다. 최신 배포본은 **042 개발판**이며, 건담 작품·게임 타이틀 로고는 원본으로 유지합니다.

최신 로컬·공개 작업본은 **042**입니다. 웹 AI 결과 11개를 수신한 뒤 실제 원문·그림으로 감독 검수해 텍스트 51곳과 이미지 250면을 반영했습니다. 기체·파일럿 이름판 232개, 조작 안내의 오역, 지도·미션·결과·설정 UI를 보완했습니다. 정적 검사·원판용 xdelta 재적용·공개 다운로드 해시 확인은 PASS입니다. [040–042 변경·검증](docs/HISTORY.md#revision-042).

## 다운로드·적용

[042 개발 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-08-graphics-042) · [042 xdelta 다운로드](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/download/dev-2026-10-08-graphics-042/next_plus_graphics_revision_042.xdelta)

합법적으로 보유한 **패치하지 않은 일본/아시아판 원본 ISO**에 적용하는 누적 패치입니다. 기존 패치 ISO에 덧씌우지 않고 별도 출력 파일을 만드세요. 폰트는 패치 결과 ISO에 내장됩니다.

- 원본 크기: `1,757,806,592`바이트
- 원본 SHA-256: `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3`
- 적용 순서·패치 및 출력 해시: [설치 안내](docs/INSTALL.md)

```text
xdelta3 -d -s "original_jp.iso" "next_plus_graphics_revision_042.xdelta" "next_plus_graphics_revision_042.iso"
```

`original_jp.iso`는 원본 파일명 예시입니다. 실제 원본 파일명을 사용하세요.

## 현재 상태

042는 038의 비텍스트·제어 구두점·달성 조건 복원과 전체 대사 수정을 포함한 누적 개발판입니다. 현재 번역 슬롯 3,953개, 수정 PZZ 938개·이미지 1,126면과 원본 타이틀 로고 193면 보호를 확인했습니다. [수정 범위와 근거](docs/HISTORY.md#revision-042).

**백식 호위 임무 프리징은 038에서 해결됐다는 사용자 확인을 받았습니다.** 027에서 보고된 NEXT PLUS 중급 트라이얼 마지막 백식 호위 임무의 랜덤 프리징은 [해결 확인](docs/MISSION_FREEZE_027_2026-10-05.md)으로 닫았습니다. 042의 게임 실행은 아직 미확인입니다. 과거 023의 타이거바움 해결 확인은 별도 범위입니다.

정적 검사·원판 기반 패치 재적용·공개 다운로드 해시 확인은 통과했습니다. 전체 게임·NEXT PLUS의 텍스트와 이미지 한글화 및 전체 플레이 검수는 진행 중입니다.

## 문서

| 목적 | 안내 |
|---|---|
| 다운로드·적용·이전 배포본 | [설치 안내](docs/INSTALL.md) |
| 버전별 변경·오류 수정 | [통합 변경 이력](docs/HISTORY.md) |
| 현재 진행과 다음 작업 | [진행 현황](PROGRESS.md), [현재 인계](99_HANDOFF/CURRENT.md) |
| 도구·환경·과거 패치 복구 | [개발 안내](docs/DEVELOPMENT.md), [기술 연구](docs/RESEARCH_NOTES.md) |
| 웹 AI 검수·번역·결과 반환 | [첨부 두 개로 쓰는 임무 프롬프트](docs/AI_WORKER_TASK.md) |
| 로고 처리·공개 범위 | [원본 로고 정책](docs/GUNDAM_TITLE_LOGO_POLICY.md), [배포 방침](docs/PUBLICATION_POLICY.md) |

Git에는 도구·한국어 초안·검증 집계를 공개하고, 릴리스에는 `.xdelta`만 제공합니다. 게임 ISO·추출 자산·전체 원문은 포함하지 않습니다. 공개 번역 자료는 초안이며 전부 승인·삽입됐다는 뜻은 아닙니다. 건담 및 관련 자료의 권리는 각 권리자에게 있으며 제작사·배급사와 무관한 팬 프로젝트입니다.
