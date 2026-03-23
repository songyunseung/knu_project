# 🏛️ 관공서 키오스크 - Spring 백엔드 서버

## 담당 역할
**역할 3 - Spring 백엔드 & DB (데이터 저장과 전체 흐름)**

## 개발 환경
- Java 17
- Spring Boot 3.5
- PostgreSQL 18
- WebSocket (STOMP)

## 서버 실행 방법
1. PostgreSQL 실행 (pgAdmin 4 관리자 권한으로 실행)
2. 아래 명령어 실행
```
.\gradlew bootRun
```
3. http://localhost:8080/swagger-ui/index.html 접속

## DB 세팅 방법
pgAdmin에서 아래 SQL 실행:
```sql
CREATE USER kiosk_user WITH PASSWORD 'kiosk1234';
CREATE DATABASE kioskdb OWNER kiosk_user;
GRANT ALL PRIVILEGES ON DATABASE kioskdb TO kiosk_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kiosk_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kiosk_user;
```

## API 목록

### 세션 관리
| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | /api/session/start | 세션 시작 + UI 설정 반환 |
| POST | /api/session/end | 세션 종료 |
| PUT | /api/session/{id}/accessibility | UI 설정 변경 |
| POST | /api/session/log | 행동 로그 저장 |

### 서비스/민원
| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | /api/services | 전체 서비스 목록 조회 |
| GET | /api/services/category/{id} | 카테고리별 서비스 조회 |
| POST | /api/applications | 민원 신청 접수 |
| GET | /api/applications/{applicationNo} | 민원 처리 현황 조회 |
| GET | /api/applications/session/{sessionId} | 세션별 신청 목록 |

## 사용자 유형별 자동 UI 설정
| 유형 | largeFont | highContrast | simpleMode | lowScreenMode | fontSize |
|------|-----------|--------------|------------|---------------|----------|
| ELDERLY (고령자) | true | true | true | false | 24px |
| WHEELCHAIR (휠체어) | false | false | false | true | 20px |
| NORMAL (일반) | false | false | false | false | 16px |

## DB 테이블 구조
| 테이블 | 설명 |
|--------|------|
| user_sessions | 키오스크 이용 세션 기록 |
| accessibility_profiles | 사용자별 UI 설정 저장 |
| interaction_logs | 버튼 클릭, AI 응답 등 행동 기록 |
| service_categories | 서비스 카테고리 (증명서발급, 민원신청 등) |
| service_items | 서비스 항목 상세 정보 |
| civil_applications | 민원 신청 접수 기록 |
| queue_tickets | 대기번호 발급 기록 |
| faqs | 자주 묻는 질문 |
| notices | 공지사항 |
| public_info_cache | 외부 API 캐시 |
| kiosk_devices | 키오스크 장치 목록 |

## 팀원 연동 방법
- **역할 2 (MCP Server)**: `POST /api/session/start` 호출해서 세션 시작
- **역할 4 (MCP Client)**: 응답받은 UI 설정으로 화면 변경
- **역할 5 (Frontend)**: `ws://localhost:8080/ws` WebSocket 연결

## WebSocket 채널
```javascript
// React에서 연결 예시
stompClient.subscribe('/topic/ui/{sessionId}', (msg) => {
    const settings = JSON.parse(msg.body);
    // settings.largeFont, settings.fontSize 등으로 UI 변경
});
```

## 서비스 항목 목록
### 1. 증명서 발급
- 주민등록등본 (400원)
- 주민등록초본 (400원)
- 가족관계증명서 (1,000원)
- 기본증명서 (1,000원)
- 혼인관계증명서 (1,000원)
- 인감증명서 (600원)

### 2. 민원 신청
- 전입신고, 출생신고, 사망신고

### 3. 세금/납부
- 지방세 납부확인서, 납세증명서, 건강보험료 납부확인서

### 4. 복지 서비스
- 복지급여 신청, 기초생활수급자 확인