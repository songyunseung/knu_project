package com.kiosk.repository;

import com.kiosk.entity.InteractionLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface InteractionLogRepository extends JpaRepository<InteractionLog, Long> {
    List<InteractionLog> findBySessionIdOrderByCreatedAtAsc(String sessionId);
    List<InteractionLog> findBySessionIdAndActionType(String sessionId, String actionType);
}