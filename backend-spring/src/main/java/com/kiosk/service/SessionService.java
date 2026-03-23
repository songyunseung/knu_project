package com.kiosk.service;

import com.kiosk.entity.AccessibilityProfile;
import com.kiosk.entity.AccessibilityProfile.UserType;
import com.kiosk.entity.InteractionLog;
import com.kiosk.entity.UserSession;
import com.kiosk.repository.AccessibilityProfileRepository;
import com.kiosk.repository.InteractionLogRepository;
import com.kiosk.repository.UserSessionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class SessionService {

    private final UserSessionRepository sessionRepository;
    private final AccessibilityProfileRepository profileRepository;
    private final InteractionLogRepository logRepository;

    public SessionService(UserSessionRepository sessionRepository,
                          AccessibilityProfileRepository profileRepository,
                          InteractionLogRepository logRepository) {
        this.sessionRepository = sessionRepository;
        this.profileRepository = profileRepository;
        this.logRepository = logRepository;
    }

    @Transactional
    public Map<String, Object> startSession(String deviceId, String detectedType) {
        String sessionId = UUID.randomUUID().toString();

        UserSession session = UserSession.builder()
                .sessionId(sessionId)
                .deviceId(deviceId)
                .detectedType(detectedType)
                .build();
        sessionRepository.save(session);

        UserType userType = parseUserType(detectedType);
        AccessibilityProfile profile = buildProfileByUserType(sessionId, deviceId, userType);
        profileRepository.save(profile);

        Map<String, Object> result = new HashMap<>();
        result.put("sessionId",     sessionId);
        result.put("userType",      userType.name());
        result.put("largeFont",     profile.getLargeFont());
        result.put("highContrast",  profile.getHighContrast());
        result.put("simpleMode",    profile.getSimpleMode());
        result.put("voiceGuide",    profile.getVoiceGuide());
        result.put("lowScreenMode", profile.getLowScreenMode());
        result.put("fontSize",      profile.getFontSize());
        return result;
    }

    @Transactional
    public void endSession(String sessionId) {
        sessionRepository.findBySessionId(sessionId).ifPresent(session -> {
            LocalDateTime now = LocalDateTime.now();
            long duration = Duration.between(session.getStartedAt(), now).getSeconds();
            session.setEndedAt(now);
            session.setDurationSec((int) duration);
            session.setIsCompleted(true);
            sessionRepository.save(session);
        });
    }

    @Transactional
    public void updateAccessibility(String sessionId, UserType userType,
                                    Boolean largeFont, Boolean highContrast,
                                    Boolean simpleMode, Boolean voiceGuide,
                                    Boolean lowScreenMode, Integer fontSize) {
        profileRepository.findBySessionId(sessionId).ifPresent(profile -> {
            if (userType      != null) profile.setUserType(userType);
            if (largeFont     != null) profile.setLargeFont(largeFont);
            if (highContrast  != null) profile.setHighContrast(highContrast);
            if (simpleMode    != null) profile.setSimpleMode(simpleMode);
            if (voiceGuide    != null) profile.setVoiceGuide(voiceGuide);
            if (lowScreenMode != null) profile.setLowScreenMode(lowScreenMode);
            if (fontSize      != null) profile.setFontSize(fontSize);
            profileRepository.save(profile);
        });
    }

    @Transactional
    public void saveLog(String sessionId, String actionType, String actionDetail,
                        String aiResponse, Integer responseTime) {
        InteractionLog interactionLog = InteractionLog.builder()
                .sessionId(sessionId)
                .actionType(actionType)
                .actionDetail(actionDetail)
                .aiResponse(aiResponse)
                .responseTime(responseTime)
                .build();
        logRepository.save(interactionLog);
    }

    private UserType parseUserType(String detectedType) {
        if (detectedType == null) return UserType.NORMAL;
        try {
            return UserType.valueOf(detectedType.toUpperCase());
        } catch (IllegalArgumentException e) {
            return UserType.NORMAL;
        }
    }

    private AccessibilityProfile buildProfileByUserType(
            String sessionId, String deviceId, UserType userType) {

        AccessibilityProfile.Builder builder = AccessibilityProfile.builder()
                .sessionId(sessionId)
                .deviceId(deviceId)
                .userType(userType);

        return switch (userType) {
            case ELDERLY ->           // 고령자: 큰 글씨 + 고대비 + 단순모드 + 음성
                builder.largeFont(true).highContrast(true)
                    .simpleMode(true).voiceGuide(true).fontSize(24).build();
            case WHEELCHAIR ->        // 휠체어: 낮은 화면 모드
                builder.lowScreenMode(true).fontSize(20).build();
            default ->                // 일반
                builder.fontSize(16).build();
        };
    }
}