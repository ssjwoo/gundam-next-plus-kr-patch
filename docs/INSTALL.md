# 한글패치 설치 안내

현재 정식 버전은 **v1.0.0**입니다. [릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/v1.0.0)에서 [gundam_next_plus_ko_v1.0.0.xdelta](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/download/v1.0.0/gundam_next_plus_ko_v1.0.0.xdelta)를 내려받으세요.

기존 042 패치와 내용이 같습니다. 이미 042를 적용했다면 다시 패치할 필요가 없습니다. 사용자가 042를 간단히 플레이한 뒤 정식 배포를 승인했습니다. **백식 호위 임무 프리징은 038에서 해결 확인을 받았습니다.** [해결 기록](MISSION_FREEZE_027_2026-10-05.md).

## 지원 원본

합법적으로 보유한 **패치하지 않은 NPJH50107 일본/아시아판 ISO**에 적용하는 누적 패치입니다. 파일명보다 아래 크기와 해시가 일치해야 합니다. 이전 패치 ISO에 덧씌우지 않고 새 출력 파일을 만드세요.

| 구분 | 크기(바이트) | CRC32 | SHA-256 |
|---|---:|---|---|
| 원본 ISO | 1,757,806,592 | `F9D9B854` | `a00c38959d52377b65f9afb5223e02c4ac5a876b8a33c998a7fe3f07dbf1feb3` |
| 출력 ISO | 1,757,806,592 | `87C3C2B8` | `86b0b410d965d9b3947c5c088e736ae29173590b9489df27f7dd8d42b34f6e9b` |
| v1.0.0 패치 | 15,273,684 | `57A36B08` | `eb2f1765be5f4efc0820b327edd0c06cbbccd4c27fbb90cb8df5423642eb12a8` |

## 적용 순서

1. 원본 ISO를 보존하고 xdelta 패처에서 원본 파일, 위 `.xdelta`, 새 출력 ISO 경로를 선택합니다.
2. 명령줄을 사용한다면 다음과 같이 적용합니다. 파일 경로에 공백이 있으면 따옴표로 감싸세요.
3. 출력의 크기·해시를 위 표와 비교한 뒤 PSP 또는 PPSSPP에서 실행합니다.

```text
xdelta3 -d -s "original_jp.iso" "gundam_next_plus_ko_v1.0.0.xdelta" "gundam_next_plus_ko_v1.0.0.iso"
```

`original_jp.iso`는 명령의 원본 파일명 예시입니다. 실제 원본 파일명을 사용하세요. 폰트는 결과 ISO의 `/PSP_GAME/SYSDIR/UPDATE/DATA.BIN`에 내장되므로 별도 PSP 폰트 추출은 필요하지 않습니다.

적용에 실패하면 먼저 원본 해시를 확인하세요. 게임 문제를 보고할 때는 패치 버전, 기기, 발생 미션·상황을 함께 알려주세요.

## 확인 범위와 후속 업데이트

v1.0.0은 원판 기반 패치 재적용과 정적 검사를 통과한 내부 빌드 042입니다. 웹 AI 감독 검수로 텍스트 51곳과 이미지 250면·440문구를 추가 보완했으며 원본 타이틀 로고를 유지합니다.

일부 영문·작은 이미지 표식과 문맥 보완은 후속 업데이트 대상이며 전체 게임 완주 검수는 별도 범위입니다. [주요 변경](../CHANGELOG.md), [상세 수정·검증](HISTORY.md#release-v1-0-0), [진행 현황](../PROGRESS.md).

## 이전 배포본

| 버전 | 배포 페이지 | 확인 범위 |
|---|---|---|
| 042 | [2026-10-08 개발 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-08-graphics-042) | v1.0.0과 동일한 패치 |
| 038 | [2026-10-05 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-05-graphics-038) | 백식 호위 임무 프리징 해결 사용자 확인 |
| 027 | [2026-10-04 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-04-graphics-027) | 백식 호위 임무에서 랜덤 프리징 보고 |
| 023 | [2026-10-03 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-023) | 사용자 요청 수정 및 이전 타이거바움 프리징 해결 확인 |
| 021 | [2026-10-03 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-10-03-graphics-021) | 첫 로딩 수정 확인; 후속 전투 프리징 보고 |
| v19 | [2026-09-26 릴리스](https://github.com/ssjwoo/gundam-next-plus-kr-patch/releases/tag/dev-2026-09-26) | 초기 폰트·텍스트 개발판 |

버전별 변경과 검증 근거는 [통합 변경 이력](HISTORY.md)에 있습니다. 릴리스 자산은 `.xdelta`만 제공하며 전체 ISO·추출 자산은 배포하지 않습니다. [공개 방침](PUBLICATION_POLICY.md).
