package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.RecycleBinSettings;
import com.taffy.music.mapper.RecycleBinSettingsMapper;
import com.taffy.music.service.RecycleBinSettingsService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
public class RecycleBinSettingsServiceImpl extends ServiceImpl<RecycleBinSettingsMapper, RecycleBinSettings> implements RecycleBinSettingsService {

    @Override
    public RecycleBinSettings getSettings() {
        // 假设设置表只有一条记录，ID 通常为 1 或直接取第一条
        // 如果没有记录，可以返回一个默认配置或 null
        RecycleBinSettings settings = getOne(new LambdaQueryWrapper<RecycleBinSettings>().last("LIMIT 1"));
        if (settings == null) {
            log.warn("Recycle bin settings not found in database, returning default values.");
            // 创建一个包含默认值的设置对象
            settings = new RecycleBinSettings();
            settings.setId(null); // ID 应为 null，因为这是内存中的默认对象
            settings.setDefaultRetentionDays(30); // 默认保留 30 天
            settings.setAutoCleanupEnabled(true); // 默认启用自动清理
            settings.setAutoCleanupTime(java.time.LocalTime.parse("03:00:00")); // 默认清理时间
        }
        return settings;
    }

    @Override
    @Transactional
    public RecycleBinSettings updateSettings(RecycleBinSettings newSettings) {
        if (newSettings == null) {
            throw new IllegalArgumentException("Settings cannot be null");
        }

        // 查找现有设置，通常只有一条记录
        RecycleBinSettings existingSettings = getOne(new LambdaQueryWrapper<RecycleBinSettings>().last("LIMIT 1"));

        if (existingSettings != null) {
            // 更新现有设置
            existingSettings.setDefaultRetentionDays(newSettings.getDefaultRetentionDays());
            existingSettings.setAutoCleanupEnabled(newSettings.getAutoCleanupEnabled());
            existingSettings.setAutoCleanupTime(newSettings.getAutoCleanupTime());
            // update_time 会自动更新
            updateById(existingSettings);
            return existingSettings;
        } else {
            // 如果没有现有设置，则插入新的设置
            log.info("No existing recycle bin settings found, creating new settings record.");
            // create_time 和 update_time 默认是 CURRENT_TIMESTAMP
            save(newSettings);
            // 返回保存后的对象，此时应该有 ID 了
            return newSettings;
        }
    }
} 