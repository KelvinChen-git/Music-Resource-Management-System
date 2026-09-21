package com.taffy.music.service.impl;


import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.mapper.FileChunkMapper;
import com.taffy.music.service.FileChunkService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collection;
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
    public boolean isChunkUploaded(Long fileId, Integer chunkIndex) {
        LambdaQueryWrapper<FileChunk> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileChunk::getFileId, fileId)
                .eq(FileChunk::getChunkIndex, chunkIndex)
                .eq(FileChunk::getStatus, 1);
        return count(wrapper) > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean saveBatch(Collection<FileChunk> chunks) {
        // 防御性拷贝：将 Collection 转为 List
        List<FileChunk> chunkList = new ArrayList<>(chunks);
        int affectedRows = baseMapper.insertBatchSomeColumn(chunkList);
        return affectedRows > 0;
}
    
} 