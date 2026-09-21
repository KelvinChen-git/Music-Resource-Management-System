package com.taffy.music.service;

import com.taffy.music.domain.RecycleBinSettings;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/**
 * 回收站自动清理定时任务
 */
@Slf4j
@Component
public class RecycleBinCleanupTask {
    
    @Autowired
    private RecycleBinService recycleBinService;
    
    @Autowired
    private RecycleBinSettingsService recycleBinSettingsService;
    
    /**
     * 每天凌晨3点自动清理过期项目
     * 实际执行时间会根据设置调整
     */
    @Scheduled(cron = "0 0 0/1 * * ?")  // 每小时执行一次，检查是否需要清理
    public void cleanupExpiredItems() {
        try {
            // 获取回收站设置
            RecycleBinSettings settings = recycleBinSettingsService.getSettings();
            
            // 如果自动清理被禁用，直接返回
            if (settings == null || !settings.getAutoCleanupEnabled()) {
                log.debug("回收站自动清理功能已禁用");
                return;
            }
            
            // 获取当前时间
            LocalTime now = LocalTime.now();
            LocalTime cleanupTime = settings.getAutoCleanupTime();
            
            // 检查是否到达清理时间（允许5分钟误差）
            if (Math.abs(now.getHour() - cleanupTime.getHour()) > 0 || 
                    (now.getHour() == cleanupTime.getHour() && Math.abs(now.getMinute() - cleanupTime.getMinute()) > 5)) {
                // 不在清理时间范围内
                return;
            }
            
            log.info("开始执行回收站自动清理任务，当前时间: {}", 
                    LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            
            // 执行清理操作
            int cleanedCount = recycleBinService.autoCleanupExpiredItems();
            
            log.info("回收站自动清理完成，共清理 {} 个过期项目", cleanedCount);
        } catch (Exception e) {
            log.error("回收站自动清理任务执行失败", e);
        }
    }
} 