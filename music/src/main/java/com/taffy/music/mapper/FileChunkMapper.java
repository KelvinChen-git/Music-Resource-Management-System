package com.taffy.music.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taffy.music.domain.FileChunk;
import org.apache.ibatis.annotations.Mapper;

/** 文件分片使用 MyBatis Plus 已注册的标准 CRUD 映射。 */
@Mapper
public interface FileChunkMapper extends BaseMapper<FileChunk> {
}
