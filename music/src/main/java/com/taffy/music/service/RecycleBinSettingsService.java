package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.RecycleBinSettings;

/**
 * 回收站设置服务接口
 */
public interface RecycleBinSettingsService extends IService<RecycleBinSettings> {

    /**
     * 获取当前回收站设置
     * @return 当前设置，如果不存在则返回null或默认值
     */
    RecycleBinSettings getSettings();

    /**
     * 更新回收站设置
     * @param settings 新的设置对象
     * @return 更新后的设置对象
     */
    RecycleBinSettings updateSettings(RecycleBinSettings settings);
} 