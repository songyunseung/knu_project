package com.kiosk.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "civil_applications")
public class CivilApplication {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "application_no", unique = true, nullable = false, length = 50)
    private String applicationNo;          // 접수번호 (CIV-20260318-001)

    @Column(name = "session_id", length = 100)
    private String sessionId;

    @Column(name = "service_item_id")
    private Long serviceItemId;            // 어떤 서비스인지

    @Column(name = "applicant_name", length = 100)
    private String applicantName;          // 신청인 이름

    @Column(name = "status", length = 50)
    private String status = "RECEIVED";
    // RECEIVED: 접수
    // PROCESSING: 처리중
    // COMPLETED: 완료
    // CANCELLED: 취소

    @Column(name = "copies")
    private Integer copies = 1;            // 발급 부수

    @Column(name = "purpose", length = 200)
    private String purpose;                // 발급 목적 (금융제출용 등)

    @Column(name = "fee_paid")
    private Integer feePaid = 0;           // 납부한 수수료

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
    }

    // Getters
    public Long getId() { return id; }
    public String getApplicationNo() { return applicationNo; }
    public String getSessionId() { return sessionId; }
    public Long getServiceItemId() { return serviceItemId; }
    public String getApplicantName() { return applicantName; }
    public String getStatus() { return status; }
    public Integer getCopies() { return copies; }
    public String getPurpose() { return purpose; }
    public Integer getFeePaid() { return feePaid; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getCompletedAt() { return completedAt; }

    // Setters
    public void setStatus(String status) { this.status = status; }
    public void setCompletedAt(LocalDateTime v) { this.completedAt = v; }

    // Builder
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private final CivilApplication a = new CivilApplication();
        public Builder applicationNo(String v) { a.applicationNo = v; return this; }
        public Builder sessionId(String v) { a.sessionId = v; return this; }
        public Builder serviceItemId(Long v) { a.serviceItemId = v; return this; }
        public Builder applicantName(String v) { a.applicantName = v; return this; }
        public Builder copies(Integer v) { a.copies = v; return this; }
        public Builder purpose(String v) { a.purpose = v; return this; }
        public Builder feePaid(Integer v) { a.feePaid = v; return this; }
        public CivilApplication build() { return a; }
    }
}