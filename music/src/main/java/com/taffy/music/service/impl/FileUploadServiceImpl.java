package com.taffy.music.service.impl;


import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.mapper.FileUploadMapper;
import com.taffy.music.service.FileUploadService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 文件上传Service实现类
 */
@Service
public class FileUploadServiceImpl extends ServiceImpl<FileUploadMapper, FileUpload> implements FileUploadService {
    
    @Override
    public FileUpload getByFileMd5(String fileMd5) {
        LambdaQueryWrapper<FileUpload> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileUpload::getFileMd5, fileMd5);
        return getOne(wrapper);
    }
    
    @Override
    public boolean updateStatus(Long id, Integer status) {
        FileUpload fileUpload = new FileUpload();
        fileUpload.setId(id);
        fileUpload.setStatus(status);
        if (status == 1) { // 上传完成
            fileUpload.setCompleteTime(LocalDateTime.now());
        }
        return updateById(fileUpload);
    }
    
    @Override
public boolean incrementUploadedChunks(Long id) {
    // 1. 先查询完整对象
    FileUpload file = getById(id);
    if (file == null) {
        return false; // 文件不存在，直接返回 false
    }
    // 2. 修改需要更新的字段
    file.setUploadedChunks(file.getUploadedChunks() + 1);
    // 3. 执行更新操作
    return updateById(file);
}
    
    @Override
    public FileUpload getByFilePath(String filePath) {
        LambdaQueryWrapper<FileUpload> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FileUpload::getFilePath, filePath);
        // 默认情况下 getOne 会添加 LIMIT 1
        return getOne(wrapper);
    }
} 