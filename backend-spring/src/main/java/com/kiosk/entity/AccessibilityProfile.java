package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "accessibility_profiles")
public class AccessibilityProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 100)
    private String deviceId;

    @Column(name = "session_id", length = 100)
    private String sessionId;

    @Enumerated(EnumType.STRING)
    @Column(name = "user_type", nullable = false, length = 50)
    private UserType userType;

    @Column(name = "large_font")
    private Boolean largeFont = false;

    @Column(name = "high_contrast")
    private Boolean highContrast = false;

    @Column(name = "simple_mode")
    private Boolean simpleMode = false;

    @Column(name = "voice_guide")
    private Boolean voiceGuide = false;

    @Column(name = "low_screen_mode")
    private Boolean lowScreenMode = false;      // 휠체어용 낮은 화면

    @Column(name = "font_size")
    private Integer fontSize = 16;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public enum UserType {
        ELDERLY,            // 고령자 → 확대 + 고대비
        WHEELCHAIR,         // 휠체어 → 낮은 화면 모드
        NORMAL              // 일반
    }

    // Getters
    public Long getId() { return id; }
    public String getDeviceId() { return deviceId; }
    public String getSessionId() { return sessionId; }
    public UserType getUserType() { return userType; }
    public Boolean getLargeFont() { return largeFont; }
    public Boolean getHighContrast() { return highContrast; }
    public Boolean getSimpleMode() { return simpleMode; }
    public Boolean getVoiceGuide() { return voiceGuide; }
    public Boolean getLowScreenMode() { return lowScreenMode; }
    public Integer getFontSize() { return fontSize; }

    // Setters
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    public void setUserType(UserType userType) { this.userType = userType; }
    public void setLargeFont(Boolean largeFont) { this.largeFont = largeFont; }
    public void setHighContrast(Boolean highContrast) { this.highContrast = highContrast; }
    public void setSimpleMode(Boolean simpleMode) { this.simpleMode = simpleMode; }
    public void setVoiceGuide(Boolean voiceGuide) { this.voiceGuide = voiceGuide; }
    public void setLowScreenMode(Boolean lowScreenMode) { this.lowScreenMode = lowScreenMode; }
    public void setFontSize(Integer fontSize) { this.fontSize = fontSize; }

    // Builder
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final AccessibilityProfile p = new AccessibilityProfile();
        public Builder sessionId(String v) { p.sessionId = v; return this; }
        public Builder deviceId(String v) { p.deviceId = v; return this; }
        public Builder userType(UserType v) { p.userType = v; return this; }
        public Builder largeFont(Boolean v) { p.largeFont = v; return this; }
        public Builder highContrast(Boolean v) { p.highContrast = v; return this; }
        public Builder simpleMode(Boolean v) { p.simpleMode = v; return this; }
        public Builder voiceGuide(Boolean v) { p.voiceGuide = v; return this; }
        public Builder lowScreenMode(Boolean v) { p.lowScreenMode = v; return this; }
        public Builder fontSize(Integer v) { p.fontSize = v; return this; }
        public AccessibilityProfile build() { return p; }
    }
}