package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.mapper.FileChunkMapper;
import com.taffy.music.service.FileChunkService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 文件分片Service实现类
 */
@Service
public class FileChunkServiceImpl extends ServiceImpl<FileChunkMapper, FileChunk> implements FileChunkService {
    
    @Override
    public List<FileChunk> getChunksByFileId(Long fileId) {
        LambdaQueryWrapper<FileChunk> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileChunk::getFileId, fileId)
                .orderByAsc(FileChunk::getChunkIndex);
        return list(wrapper);
    }

    @Override
    public List<FileChunk> getChunksByFileIdForUpdate(Long fileId) {
        // Authentication may already have established a REPEATABLE READ snapshot
        // before the parent lock was acquired. Use a current read after that lock.
        LambdaQueryWrapper<FileChunk> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileChunk::getFileId, fileId)
                .orderByAsc(FileChunk::getChunkIndex)
                .last("FOR UPDATE");
        return list(wrapper);
    }

    @Override
    public boolean isChunkUploaded(Long fileId, Integer chunkIndex) {
        LambdaQueryWrapper<FileChunk> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileChunk::getFileId, fileId)
                .eq(FileChunk::getChunkIndex, chunkIndex)
                .eq(FileChunk::getStatus, 1);
        return count(wrapper) > 0;
    }

}
