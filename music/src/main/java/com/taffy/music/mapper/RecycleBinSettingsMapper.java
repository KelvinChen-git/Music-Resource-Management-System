package com.taffy.music.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taffy.music.domain.RecycleBinSettings;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RecycleBinSettingsMapper extends BaseMapper<RecycleBinSettings> {
    // 基本的CRUD操作由BaseMapper提供
} 