package com.kiosk.repository;

import com.kiosk.entity.UserSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserSessionRepository extends JpaRepository<UserSession, Long> {
    Optional<UserSession> findBySessionId(String sessionId);
    List<UserSession> findByDeviceIdOrderByStartedAtDesc(String deviceId);
    List<UserSession> findByDeviceIdAndIsCompletedFalse(String deviceId);
}