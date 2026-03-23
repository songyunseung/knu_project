package com.kiosk.repository;

import com.kiosk.entity.AccessibilityProfile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface AccessibilityProfileRepository extends JpaRepository<AccessibilityProfile, Long> {
    Optional<AccessibilityProfile> findBySessionId(String sessionId);
    Optional<AccessibilityProfile> findTopByDeviceIdOrderByCreatedAtDesc(String deviceId);
}