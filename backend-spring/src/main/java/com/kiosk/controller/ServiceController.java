package com.kiosk.controller;

import com.kiosk.entity.CivilApplication;
import com.kiosk.entity.ServiceItem;
import com.kiosk.repository.CivilApplicationRepository;
import com.kiosk.repository.ServiceItemRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ServiceController {

    private final ServiceItemRepository serviceItemRepository;
    private final CivilApplicationRepository applicationRepository;

    public ServiceController(ServiceItemRepository serviceItemRepository,
                             CivilApplicationRepository applicationRepository) {
        this.serviceItemRepository = serviceItemRepository;
        this.applicationRepository = applicationRepository;
    }

    // GET /api/services
    // 키오스크에서 이용 가능한 전체 서비스 목록 조회
    @GetMapping("/services")
    public ResponseEntity<List<ServiceItem>> getAllServices() {
        return ResponseEntity.ok(
            serviceItemRepository.findByIsAvailableTrueOrderBySortOrder()
        );
    }

    // GET /api/services/category/{categoryId}
    // 카테고리별 서비스 목록 조회
    // 1: 증명서발급, 2: 민원신청, 3: 세금/납부, 4: 복지서비스
    @GetMapping("/services/category/{categoryId}")
    public ResponseEntity<List<ServiceItem>> getServicesByCategory(
            @PathVariable Long categoryId) {
        return ResponseEntity.ok(
            serviceItemRepository.findByCategoryIdOrderBySortOrder(categoryId)
        );
    }

    // POST /api/applications
    // 민원 신청 접수
    @PostMapping("/applications")
    public ResponseEntity<Map<String, Object>> createApplication(
            @RequestBody Map<String, Object> request) {

        String today = LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String applicationNo = "CIV-" + today + "-"
                + String.format("%03d", (int)(Math.random() * 999 + 1));

        CivilApplication application = CivilApplication.builder()
                .applicationNo(applicationNo)
                .sessionId((String) request.get("sessionId"))
                .serviceItemId(Long.valueOf(request.get("serviceItemId").toString()))
                .applicantName((String) request.get("applicantName"))
                .copies(request.get("copies") != null
                        ? (Integer) request.get("copies") : 1)
                .purpose((String) request.get("purpose"))
                .feePaid(request.get("feePaid") != null
                        ? (Integer) request.get("feePaid") : 0)
                .build();

        applicationRepository.save(application);

        Map<String, Object> result = new HashMap<>();
        result.put("success",       true);
        result.put("applicationNo", applicationNo);
        result.put("message",       "민원이 정상적으로 접수되었습니다");
        return ResponseEntity.ok(result);
    }

    // GET /api/applications/{applicationNo}
    // 접수번호로 민원 처리 현황 조회
    @GetMapping("/applications/{applicationNo}")
    public ResponseEntity<Map<String, Object>> getApplication(
            @PathVariable String applicationNo) {

        return applicationRepository.findByApplicationNo(applicationNo)
                .map(app -> {
                    Map<String, Object> result = new HashMap<>();
                    result.put("applicationNo", app.getApplicationNo());
                    result.put("status",        app.getStatus());
                    result.put("copies",        app.getCopies());
                    result.put("purpose",
                            app.getPurpose() != null ? app.getPurpose() : "");
                    result.put("feePaid",       app.getFeePaid());
                    result.put("createdAt",     app.getCreatedAt().toString());
                    return ResponseEntity.ok(result);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // GET /api/applications/session/{sessionId}
    // 세션별 신청 목록 조회
    @GetMapping("/applications/session/{sessionId}")
    public ResponseEntity<List<CivilApplication>> getApplicationsBySession(
            @PathVariable String sessionId) {
        return ResponseEntity.ok(
            applicationRepository.findBySessionId(sessionId)
        );
    }
}