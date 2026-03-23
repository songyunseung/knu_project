package com.kiosk.websocket;

import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class WebSocketNotifier {

    private final SimpMessagingTemplate messagingTemplate;

    public WebSocketNotifier(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void sendUiUpdate(String sessionId, Map<String, Object> uiSettings) {
        messagingTemplate.convertAndSend("/topic/ui/" + sessionId, uiSettings);
    }

    public void sendAiResponse(String sessionId, String responseText) {
        messagingTemplate.convertAndSend("/topic/ai/" + sessionId, Map.of(
            "type", "AI_RESPONSE",
            "text", responseText
        ));
    }
}