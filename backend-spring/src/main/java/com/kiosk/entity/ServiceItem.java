package com.kiosk.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "service_items")
public class ServiceItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "category_id")
    private Long categoryId;

    @Column(name = "name", nullable = false, length = 200)
    private String name;                    // 주민등록등본

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;            // 서비스 설명

    @Column(name = "fee")
    private Integer fee;                   // 수수료 (원)

    @Column(name = "required_docs", columnDefinition = "TEXT")
    private String requiredDocs;           // 필요 서류

    @Column(name = "processing_time", length = 100)
    private String processingTime;         // 처리 시간 (즉시발급 등)

    @Column(name = "is_available")
    private Boolean isAvailable;           // 키오스크 발급 가능 여부

    @Column(name = "sort_order")
    private Integer sortOrder;

    // Getters
    public Long getId() { return id; }
    public Long getCategoryId() { return categoryId; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public Integer getFee() { return fee; }
    public String getRequiredDocs() { return requiredDocs; }
    public String getProcessingTime() { return processingTime; }
    public Boolean getIsAvailable() { return isAvailable; }
    public Integer getSortOrder() { return sortOrder; }
}