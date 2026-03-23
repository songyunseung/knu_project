package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_sessions")
public class UserSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", unique = true, nullable = false, length = 100)
    private String sessionId;

    @Column(name = "device_id", nullable = false, length = 100)
    private String deviceId;

    @Column(name = "detected_type", length = 50)
    private String detectedType;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @Column(name = "duration_sec")
    private Integer durationSec;

    @Column(name = "is_completed")
    private Boolean isCompleted = false;

    @PrePersist
    public void prePersist() {
        this.startedAt = LocalDateTime.now();
    }

    // Getters
    public String getSessionId() { return sessionId; }
    public String getDeviceId() { return deviceId; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public Boolean getIsCompleted() { return isCompleted; }

    // Setters
    public void setEndedAt(LocalDateTime v) { this.endedAt = v; }
    public void setDurationSec(Integer v) { this.durationSec = v; }
    public void setIsCompleted(Boolean v) { this.isCompleted = v; }

    // Builder
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final UserSession s = new UserSession();
        public Builder sessionId(String v) { s.sessionId = v; return this; }
        public Builder deviceId(String v) { s.deviceId = v; return this; }
        public Builder detectedType(String v) { s.detectedType = v; return this; }
        public UserSession build() { return s; }
    }
}