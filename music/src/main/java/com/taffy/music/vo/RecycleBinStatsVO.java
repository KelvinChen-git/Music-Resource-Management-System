package com.taffy.music.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 回收站统计数据VO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecycleBinStatsVO {
    
    /**
     * 回收站项目总数
     */
    private Long totalItems;
    
    /**
     * 即将过期的项目数量（7天内）
     */
    private Long expiringItems;
    
    /**
     * 上次清理时间
     */
    private LocalDateTime lastCleanupTime;
    
    /**
     * 上次清理数量
     */
    private Integer lastCleanupCount;
    
    /**
     * 已恢复项目数量
     */
    private Long recoveredItems;
    
    /**
     * 已永久删除项目数量
     */
    private Long permanentlyDeletedItems;
} 