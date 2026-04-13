import { Client } from '@stomp/stompjs';
import { LOCAL_SERVICE_CATEGORIES, USER_TYPES } from '../data/options';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';

/**
 * README 기준
 * - broker prefix: /topic
 * - application prefix: /app
 *
 * 프론트는 서버가 보내는 UI 명령을 구독
 * 프론트는 서버로 이벤트를 발행
 */
const TOPICS = {
  uiGlobal: '/topic/ui/global', //모든 화면에 공통으로 메시지
  uiSession: (sessionId) => `/topic/ui/${sessionId}`, //특정세션에만 오는 메시지
};

const DESTINATIONS = {
  frontEvents: '/app/front/events',
  frontAck: '/app/front/ack',

  // 아래는 README에 명시된 건 아니고,
  // 기존 api 함수명을 유지하기 위한 "비즈니스용" 기본 경로 가정값임.
  // 백엔드 MessageMapping 이름이 다르면 이것만 바꾸면 됨.
  sessionStart: '/app/session/start',
  sessionEnd: '/app/session/end',
  sessionAccessibility: '/app/session/accessibility',
  sessionLog: '/app/session/log',
  services: '/app/services',
  servicesByCategory: '/app/services/category',
  applicationsCreate: '/app/applications/create',
  applicationsStatus: '/app/applications/status',
  applicationsBySession: '/app/applications/session',
};

//현재 연결상태 변수
let client = null;
let connectPromise = null;
let isConnected = false;

const pendingRequests = new Map();
const activeSubscriptions = new Map();

//requestId 생성함수 : 각 요청마다의 고유번호 생성
function makeRequestId(prefix = 'req') {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

//JSON 파싱 함수
function safeJsonParse(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function ensureClient() {
  if (client) return client;

  client = new Client({
    brokerURL: WS_URL,
    reconnectDelay: 5000,
    heartbeatIncoming: 4000,
    heartbeatOutgoing: 4000,
    debug: () => {},
  });

  client.onConnect = () => {
    isConnected = true;
  };

  client.onWebSocketClose = () => {
    isConnected = false;
    connectPromise = null;
  };

  client.onWebSocketError = (error) => {
    console.error('WebSocket error:', error);
  };

  client.onStompError = (frame) => {
    console.error('Broker reported error:', frame.headers?.message, frame.body);
  };

  return client;
}

export async function connectStomp() {
  if (client && isConnected) return client;
  if (connectPromise) return connectPromise;

  const stompClient = ensureClient();

  connectPromise = new Promise((resolve, reject) => {
    let settled = false;

    const cleanup = () => {
      stompClient.onConnect = originalOnConnect;
      stompClient.onWebSocketError = originalOnWebSocketError;
    };

    const originalOnConnect = stompClient.onConnect;
    const originalOnWebSocketError = stompClient.onWebSocketError;

    stompClient.onConnect = (frame) => {
      isConnected = true;
      originalOnConnect?.(frame);
      if (!settled) {
        settled = true;
        cleanup();
        resolve(stompClient);
      }
    };

    stompClient.onWebSocketError = (error) => {
      originalOnWebSocketError?.(error);
      if (!settled) {
        settled = true;
        cleanup();
        reject(new Error('WebSocket 연결 실패'));
      }
    };

    stompClient.activate();
  });

  return connectPromise;
}

export function disconnectStomp() {
  if (client) {
    client.deactivate();
  }
  client = null;
  connectPromise = null;
  isConnected = false;
  pendingRequests.clear();
  activeSubscriptions.clear();
}

/**
 * 공통 발행
 */
//메시지 보내기 함수
async function publish(destination, body) {
  const stomp = await connectStomp();
  stomp.publish({
    destination,
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

/**
 * 공통 request-response
 *
 * 가정:
 * - 백엔드가 응답을 /topic/front/ack 로 보내거나
 * - 최소한 requestId를 되돌려준다.
 *
 * 실제 응답 구조가 다르면 여기만 수정하면 됨.
 */
async function requestResponse(destination, payload = {}, options = {}) {
  const stomp = await connectStomp();
  const timeoutMs = options.timeoutMs ?? 8000;
  const requestId = makeRequestId('rpc');

  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`응답 시간 초과: ${destination}`));
    }, timeoutMs);

    pendingRequests.set(requestId, {
      resolve: (data) => {
        clearTimeout(timeoutId);
        pendingRequests.delete(requestId);
        resolve(data);
      },
      reject: (error) => {
        clearTimeout(timeoutId);
        pendingRequests.delete(requestId);
        reject(error);
      },
    });

    stomp.publish({
      destination,
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        requestId,
        ...payload,
      }),
    });
  });
}

/**
 * 서버 -> 프론트 UI 명령 구독
 *
 * global: /topic/ui/global
 * session: /topic/ui/{sessionId}
 */
export async function subscribeUiCommands({ sessionId, onCommand }) {
  const stomp = await connectStomp();

  if (!activeSubscriptions.has('ui-global')) {
    const sub = stomp.subscribe(TOPICS.uiGlobal, (message) => {
      const payload = safeJsonParse(message.body);
      onCommand?.(payload);
    });
    activeSubscriptions.set('ui-global', sub);
  }

  if (sessionId) {
    const key = `ui-session-${sessionId}`;
    if (!activeSubscriptions.has(key)) {
      const sub = stomp.subscribe(TOPICS.uiSession(sessionId), (message) => {
        const payload = safeJsonParse(message.body);
        onCommand?.(payload);
      });
      activeSubscriptions.set(key, sub);
    }
  }
}

/**
 * /topic/front/ack 구독
 * - request-response 응답
 * - 일반 ACK 둘 다 처리
 */
export async function subscribeFrontAck({ onAck } = {}) {
  const stomp = await connectStomp();

  if (activeSubscriptions.has('front-ack')) return;

  const sub = stomp.subscribe('/topic/front/ack', (message) => {
    const payload = safeJsonParse(message.body);

    if (payload?.requestId && pendingRequests.has(payload.requestId)) {
      const pending = pendingRequests.get(payload.requestId);

      if (payload?.error) {
        pending.reject(new Error(payload.error));
      } else {
        pending.resolve(payload?.data ?? payload);
      }
      return;
    }

    onAck?.(payload);
  });

  activeSubscriptions.set('front-ack', sub);
}

/**
 * 프론트 활동 이벤트 전송
 * README의 action 규격 맞춤
 */
export async function sendFrontEvent(action, data = {}) {
  return publish(DESTINATIONS.frontEvents, {
    action,
    data,
    sentAt: new Date().toISOString(),
  });
}

/**
 * UI 적용 완료 ACK
 */
// 서버가 ADAPT_UI 보내면 프론트가 화면을 바끅고 sendUiAck()해서 변환 완료 했음을 알려줌
export async function sendUiAck(appliedAction, data = {}) {
  return publish(DESTINATIONS.frontAck, {
    action: 'UI_ACK',
    data: {
      appliedAction,
      ...data,
    },
    sentAt: new Date().toISOString(),
  });
}

/**
 * 접근성 액션 키 -> 실제 accessibility state 반영
 */
function buildAccessibilityFromAction(prevAccessibility = {}, actionKey) {
  const next = { ...prevAccessibility };

  if (actionKey === 'highContrast') {
    next.highContrast = !next.highContrast;
  } else if (actionKey === 'largeFont') {
    next.largeFont = !next.largeFont;
    next.fontSize = next.largeFont ? 24 : 16;
  } else if (actionKey === 'lowScreenMode') {
    next.lowScreenMode = !next.lowScreenMode;
  } else if (actionKey === 'voiceGuide') {
    next.voiceGuide = !next.voiceGuide;
  }

  return next;
}

/**
 * =========================
 * 기존 api 함수명 유지 구간
 * =========================
 */
//세션 시작 요청
export async function startSession(userType = 'NORMAL') {
  try {
    return await requestResponse(DESTINATIONS.sessionStart, { userType });
  } catch (error) {
    return {
      sessionId: `local-session-${Date.now()}`,
      accessibility: USER_TYPES[userType] || USER_TYPES.NORMAL,
      mock: true,
    };
  }
}
//세션 종료 요청
export async function endSession(sessionId) {
  if (!sessionId) return null;

  try {
    return await requestResponse(DESTINATIONS.sessionEnd, { sessionId });
  } catch {
    return null;
  }
}
//접근성 상태를 서버에 저장/전달
export async function updateAccessibility(sessionId, accessibility) {
  if (!sessionId) return accessibility;

  try {
    return await requestResponse(DESTINATIONS.sessionAccessibility, {
      sessionId,
      accessibility,
    });
  } catch {
    return accessibility;
  }
}
//시용자 행동 로그 저장
export async function saveInteractionLog(sessionId, action, payload = {}) {
  if (!sessionId) return null;

  try {
    return await requestResponse(DESTINATIONS.sessionLog, {
      sessionId,
      action,
      payload,
      createdAt: new Date().toISOString(),
    });
  } catch {
    return null;
  }
}
//서비스 목록 요청
export async function getServices() {
  try {
    return await requestResponse(DESTINATIONS.services, {});
  } catch {
    return LOCAL_SERVICE_CATEGORIES;
  }
}
//카테고리별 조회
export async function getServicesByCategory(categoryId) {
  try {
    return await requestResponse(DESTINATIONS.servicesByCategory, { categoryId });
  } catch {
    return LOCAL_SERVICE_CATEGORIES.find((category) => category.id === categoryId) || null;
  }
}
//신청 생성 : 최종 제출 눌렀을 떄 실제 신청 데이터 보내느 ㄴ함수
export async function createApplication(applicationPayload) {
  try {
    return await requestResponse(DESTINATIONS.applicationsCreate, applicationPayload);
  } catch {
    return {
      applicationNo: `APP-${Date.now()}`,
      ...applicationPayload,
      status: 'RECEIVED',
      mock: true,
    };
  }
}
//신청 상태 조회
export async function getApplicationStatus(applicationNo) {
  return requestResponse(DESTINATIONS.applicationsStatus, { applicationNo });
}
//세션별 신청 목록 조회
export async function getApplicationsBySession(sessionId) {
  return requestResponse(DESTINATIONS.applicationsBySession, { sessionId });
}

/**
 * UI 버튼 클릭용 헬퍼
 */
export async function applyAccessibilityAction(sessionId, prevAccessibility, actionKey) {
  const nextAccessibility = buildAccessibilityFromAction(prevAccessibility, actionKey);

  await sendFrontEvent('USER_TOUCH', { sessionId, actionKey });
  await updateAccessibility(sessionId, nextAccessibility);

  return nextAccessibility;
}