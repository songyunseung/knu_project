---
name: Custom issue template
about: Describe this issue template's purpose here.
title: ''
labels: ''
assignees: ''

---

---
name: "Weekly Report"
about: "주간 활동 보고서입니다."
title: "[Week N]  이름 - 주간 활동 보고서"
labels: 'weekly-report'
---

## 📅 이번 주 수행 내용 (Done)
- [ ] (역할 4 연동) STOMP 메시지 규격 확정 및 테스트 코드 작성
- [ ] (역할 2 연동) 세션 생성 MCP Tool 호출부 구현

## 🔗 파트 간 연동 및 공유 사항 (Interface)
- **대상 파트**: 2번(MCP), 5번(Front)
- **공유 내용**: 세션 ID 전달 방식 변경 (Header -> Body)

## 🆘 기술적 이슈 및 해결 방안 (Issue & Blocker)
- 이슈: 웹소켓 연결 지연 발생
- 해결: 타임아웃 설정을 5s에서 10s로 상향 조정

## 🚀 다음 주 계획 (Next Week)
- 민원 접수(전입신고) 전체 시나리오 통합 테스트
