# 과거 패치 복구용 고정 초안

`development_draft_2026-09-26_ko_only_pre_polish.jsonl`은 문장 검수 전 커밋
`afa1042933a85afe437a3867eb04f5b4433f6c2e`의 한국어 초안 4,271행을 그대로 보존한 파일이다.
ID·한국어·검수 상태만 담으며 승인된 번역을 뜻하지 않는다.

`recover_source_workbook.py`가 기존 v19·보관 패치의 삽입 표현을 대조할 때 사용한다.
현재 초안의 바뀐 문장을 과거 바이트 검색에 사용하면 일부 복구가 누락될 수 있다.
이 파일은 새 번역 편집 대상으로 사용하지 않는다.

- Git 및 현재 파일: UTF-8, LF, 425,000바이트.
- SHA-256: `d1b78ab6fca06e58a148081194a059941311b9de01b81d0252cabaf796c30166`.
- 과거 Windows CRLF 체크아웃 해시: `67ef910107d3c573a0fbe9bd3b9a216e88b564215fb1299989ff64fa206fd0a6`.

마지막 해시는 같은 내용을 CRLF로 저장한 과거 로컬 파일의 기록이다. 현재 Git 파일의 해시로 사용하지 않는다.
`.gitattributes`는 번역 자료의 줄 끝을 LF로 고정한다. 실제 명령은
[작업 복구 문서](../../docs/DEVELOPMENT.md)를 참고한다.
