package com.taffy.music.mapper;
import com.taffy.music.domain.FileChunk;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 文件分片Mapper接口
 */
@Mapper
public interface FileChunkMapper extends BaseMapper<FileChunk> {
    Integer insertBatchSomeColumn(@Param("list") List<FileChunk> list);
    
} 