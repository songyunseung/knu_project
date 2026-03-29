---
name: "Weekly Report"
about: "주간 활동 보고서입니다."
title: "[Week 1] 천호영 - 주간 활동 보고서"
labels: 'weekly-report'
---

## 📅 이번 주 수행 내용 (Done)
- [x] (역할 1 구현) Qwen3.5-9B 기반 로컬 LLM 환경 구축 및 GPU 서버에서 실행 확인
- [x] (AI 서버) FastAPI 기반 ai-server 구현 (/health, /classify/user-type, /classify/service)
- [x] (프롬프트 설계) JSON 형태로 출력되도록 프롬프트 구조 설계 및 적용
- [x] (추론 안정화) thinking 출력 제거 및 JSON-only 출력 구조 적용
- [x] (원격 연동) SSH 포트포워딩을 이용한 로컬(Spring) ↔ 원격 GPU 서버 연결 구현
- [x] (임시 운영) API 구독 전 단계로 로컬 LLM(Qwen3.5)을 활용하여 기능 테스트 환경 구성

---

## 🔗 파트 간 연동 및 공유 사항 (Interface)
- **대상 파트**: 2번(MCP), 3번(Spring), 5번(Front)
- **공유 내용**:  
  - AI 응답을 JSON 형태로 표준화하여 MCP 및 Spring에서 바로 사용 가능하도록 설계
  - serviceId 기반으로 화면 이동 가능하도록 구조 정의
  - 로컬 환경에서 `localhost:18000`으로 AI 서버 호출 가능하도록 SSH 터널 구성
  - 현재는 API 키가 없는 상태이므로 외부 API 대신 로컬 LLM을 사용하여 동일한 인터페이스 유지

---

## 🆘 기술적 이슈 및 해결 방안 (Issue & Blocker)

- 이슈: 최신 모델(Qwen3.5) 실행 시 transformers 버전 미지원 문제 발생  
- 해결: Python 3.10 환경 구성 후 transformers 최신 버전 설치

- 이슈: 로그인 서버에서 모델 실행 시 실패  
- 해결: 반드시 GPU 노드(DIS)에서 실행하도록 구조 정리

- 이슈: SSH 포트포워딩 연결 실패  
- 해결: DIS 노드 기준으로 포워딩 경로 재설정

- 이슈: 모델 출력에 think, 불필요한 텍스트 포함  
- 해결: thinking 비활성화 및 JSON 출력 강제 프롬프트 적용

- 이슈: FastAPI 실행 시 import 오류 발생  
- 해결: 파일명 오타 수정 (service_recommand → service_recommend)

---

## 🚀 다음 주 계획 (Next Week)
- Spring 백엔드와 AI 서버 완전 연동 및 API 호출 테스트
- 다양한 입력 케이스 추가하여 의도 분류 정확도 검증
- JSON 응답 구조 최종 확정 및 MCP 연동 테스트
- API 구독 이후 외부 LLM과 로컬 모델 간 성능 비교 및 전환 구조 검토