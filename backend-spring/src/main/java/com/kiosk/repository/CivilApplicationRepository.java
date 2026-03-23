package com.kiosk.repository;

import com.kiosk.entity.CivilApplication;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface CivilApplicationRepository extends JpaRepository<CivilApplication, Long> {

    // 접수번호로 조회
    Optional<CivilApplication> findByApplicationNo(String applicationNo);

    // 세션별 신청 목록 조회
    List<CivilApplication> findBySessionId(String sessionId);

    // 상태별 조회 (예: RECEIVED만 뽑기)
    List<CivilApplication> findByStatus(String status);
}