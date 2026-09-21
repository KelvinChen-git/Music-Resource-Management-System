package com.taffy.music.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taffy.music.domain.RecycleBin;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RecycleBinMapper extends BaseMapper<RecycleBin> {
    // 基本的CRUD操作由BaseMapper提供
} 