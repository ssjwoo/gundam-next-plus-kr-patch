# 패치 다운로드·적용

현재 배포본은 **038 개발판**입니다. [릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-05-graphics-038)에서 [next_plus_graphics_revision_038.xdelta](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/download/dev-2026-10-05-graphics-038/next_plus_graphics_revision_038.xdelta)를 받으세요.

038의 정적 검사·패치 재적용·공개 다운로드 확인은 통과했습니다. **038 게임 실행과 백식 호위 임무 프리징 해결은 아직 미확인입니다.** [현재 문제](MISSION_FREEZE_027_2026-10-05.md)를 참고하세요.

## 지원 원본

합법적으로 보유한 **패치하지 않은 NPJH50107 일본/아시아판 ISO**에 적용하는 누적 패치입니다. 파일명보다 아래 크기와 해시가 일치해야 합니다. 이전 패치 ISO에 덧씌우지 않고 새 출력 파일을 만드세요.

| 구분 | 크기(바이트) | CRC32 | SHA-256 |
|---|---:|---|---|
| 원본 ISO | 1,757,806,592 | `F9D9B854` | `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3` |
| 038 패치 ISO | 1,757,806,592 | `EA404316` | `96781a2918ab6999d06411f225ef432578d072f8c4c4aba24b3d3c24026ce7e2` |
| 038 xdelta | 15,156,246 | `80FAB14B` | `8c9677e709d49883f20c6ea9bc43f1f6b714aa3a34f3140a22abfc7914f4b3ea` |

## 적용 순서

1. 원본 ISO를 보존하고 xdelta 패처에서 원본 파일, 위 `.xdelta`, 새 출력 ISO 경로를 선택합니다.
2. 명령줄을 사용한다면 다음과 같이 적용합니다. 파일 경로에 공백이 있으면 따옴표로 감싸세요.
3. 출력의 크기·해시를 위 표와 비교한 뒤 PSP 또는 PPSSPP에서 실행합니다.

```text
xdelta3 -d -s "original_jp.iso" "next_plus_graphics_revision_038.xdelta" "next_plus_graphics_revision_038.iso"
```

`original_jp.iso`는 명령의 원본 파일명 예시입니다. 실제 원본 파일명을 사용하세요. 폰트는 결과 ISO의 `/PSP_GAME/SYSDIR/UPDATE/DATA.BIN`에 내장되므로 별도 PSP 폰트 추출은 필요하지 않습니다.

적용에 실패하면 먼저 원본 해시를 확인하세요. 게임 문제를 보고할 때는 패치 버전, 기기, 발생 미션·상황을 함께 알려주세요.

## 039 로컬 작업본

039는 지명 두 곳을 보정한 로컬 개발판이며 GitHub 배포본은 아직 038입니다. 같은 일본/아시아판 원본에 `next_plus_graphics_revision_039.xdelta`를 적용합니다. 로컬 결과 파일과 해시는 다음과 같습니다. 정적 검사·원판 재적용은 PASS, 실행은 NOT_TESTED입니다.

| 구분 | 크기(바이트) | CRC32 | SHA-256 |
|---|---:|---|---|
| 039 ISO | 1,757,806,592 | `6398666D` | `fa44294cc63f214f983209a95937872617d96920b942cfcd29fa9868c4e829cb` |
| 039 xdelta | 15,156,262 | `A56BDEB8` | `587a67695c539be3b7ba250153266d60eebd175d315e848304ee6d7116376576` |

[변경·검수 근거](HISTORY.md#revision-039).

## 이전 배포본

| 버전 | 배포 페이지 | 확인 범위 |
|---|---|---|
| 027 | [2026-10-04 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-04-graphics-027) | 백식 호위 임무에서 랜덤 프리징 보고 |
| 023 | [2026-10-03 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-023) | 사용자 요청 수정 및 이전 타이거바움 프리징 해결 확인 |
| 021 | [2026-10-03 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-021) | 첫 로딩 수정 확인; 후속 전투 프리징 보고 |
| v19 | [2026-09-26 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-09-26) | 초기 폰트·텍스트 개발판 |

버전별 변경과 검증 근거는 [통합 변경 이력](HISTORY.md)에 있습니다. 릴리스 자산은 `.xdelta`만 제공하며 전체 ISO·추출 자산은 배포하지 않습니다. [공개 방침](PUBLICATION_POLICY.md).
