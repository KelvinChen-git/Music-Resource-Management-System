package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.FileChunk;

import java.util.Collection;
import java.util.List;

/**
 * 文件分片服务接口
 */
public interface FileChunkService extends IService<FileChunk> {

    /**
     * 检查分片是否已上传
     * @param fileId 文件ID
     * @param chunkIndex 分片索引
     * @return 是否已上传
     */
    boolean isChunkUploaded(Long fileId, Integer chunkIndex);

    /**
     * 获取文件的所有分片
     * @param fileId 文件ID
     * @return 分片列表
     */
    List<FileChunk> getChunksByFileId(Long fileId);
    
    /**
     * 批量保存分片
     * @param chunks 分片集合
     * @return 是否成功
     */
    boolean saveBatch(Collection<FileChunk> chunks);
} 