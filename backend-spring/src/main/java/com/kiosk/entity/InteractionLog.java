package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "interaction_logs")
public class InteractionLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", nullable = false, length = 100)
    private String sessionId;

    @Column(name = "action_type", nullable = false, length = 100)
    private String actionType;

    @Column(name = "action_detail", columnDefinition = "TEXT")
    private String actionDetail;

    @Column(name = "ai_response", columnDefinition = "TEXT")
    private String aiResponse;

    @Column(name = "response_time")
    private Integer responseTime;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
    }

    // Builder
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final InteractionLog l = new InteractionLog();
        public Builder sessionId(String v) { l.sessionId = v; return this; }
        public Builder actionType(String v) { l.actionType = v; return this; }
        public Builder actionDetail(String v) { l.actionDetail = v; return this; }
        public Builder aiResponse(String v) { l.aiResponse = v; return this; }
        public Builder responseTime(Integer v) { l.responseTime = v; return this; }
        public InteractionLog build() { return l; }
    }
}