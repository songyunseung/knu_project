package com.kiosk.controller;

import com.kiosk.entity.AccessibilityProfile.UserType;
import com.kiosk.service.SessionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/session")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;

    // -------------------------------------------------------
    // POST /api/session/start
    // 사용자 감지 시 세션 시작
    // 요청 예시:
    // { "deviceId": "kiosk-001", "detectedType": "ELDERLY" }
    // detectedType: ELDERLY, WHEELCHAIR, VISUALLY_IMPAIRED,
    //               HEARING_IMPAIRED, NORMAL
    // -------------------------------------------------------
    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> startSession(
            @RequestBody Map<String, String> request) {
        String deviceId     = request.get("deviceId");
        String detectedType = request.getOrDefault("detectedType", "NORMAL");
        Map<String, Object> result = sessionService.startSession(deviceId, detectedType);
        return ResponseEntity.ok(result);
    }

    // -------------------------------------------------------
    // POST /api/session/end
    // 사용자가 자리를 뜰 때 세션 종료
    // 요청 예시: { "sessionId": "abc-123" }
    // -------------------------------------------------------
    @PostMapping("/end")
    public ResponseEntity<Map<String, Object>> endSession(
            @RequestBody Map<String, String> request) {
        sessionService.endSession(request.get("sessionId"));
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "세션이 종료되었습니다");
        return ResponseEntity.ok(result);
    }

    // -------------------------------------------------------
    // PUT /api/session/{sessionId}/accessibility
    // 사용자가 직접 UI 설정 변경 시
    // 요청 예시:
    // { "largeFont": true, "fontSize": 24 }
    // -------------------------------------------------------
    @PutMapping("/{sessionId}/accessibility")
    public ResponseEntity<Map<String, Object>> updateAccessibility(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> request) {

        sessionService.updateAccessibility(
            sessionId,
            request.get("userType") != null
                ? UserType.valueOf((String) request.get("userType")) : null,
            (Boolean) request.get("largeFont"),
            (Boolean) request.get("highContrast"),
            (Boolean) request.get("simpleMode"),
            (Boolean) request.get("voiceGuide"),
            (Boolean) request.get("lowScreenMode"),
            (Integer) request.get("fontSize")
        );

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "UI 설정이 변경되었습니다");
        return ResponseEntity.ok(result);
    }

    // -------------------------------------------------------
    // POST /api/session/log
    // 버튼 클릭, 음성 입력, AI 응답 등 행동 기록
    // 요청 예시:
    // {
    //   "sessionId": "abc-123",
    //   "actionType": "BUTTON_CLICK",
    //   "actionDetail": "주민등록등본 선택"
    // }
    // -------------------------------------------------------
    @PostMapping("/log")
    public ResponseEntity<Map<String, Object>> saveLog(
            @RequestBody Map<String, Object> request) {
        sessionService.saveLog(
            (String)  request.get("sessionId"),
            (String)  request.get("actionType"),
            (String)  request.get("actionDetail"),
            (String)  request.get("aiResponse"),
            (Integer) request.get("responseTime")
        );
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        return ResponseEntity.ok(result);
    }
}