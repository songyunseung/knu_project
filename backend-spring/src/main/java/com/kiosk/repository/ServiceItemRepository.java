package com.kiosk.repository;

import com.kiosk.entity.ServiceItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface ServiceItemRepository extends JpaRepository<ServiceItem, Long> {

    // 카테고리별 서비스 목록 조회 (정렬 순서대로)
    List<ServiceItem> findByCategoryIdOrderBySortOrder(Long categoryId);

    // 키오스크에서 이용 가능한 서비스만 조회
    List<ServiceItem> findByIsAvailableTrueOrderBySortOrder();
}