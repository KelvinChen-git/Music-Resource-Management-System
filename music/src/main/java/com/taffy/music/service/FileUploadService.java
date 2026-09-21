package com.taffy.music.service;


import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.FileUpload;

/**
 * 文件上传Service接口
 */
public interface FileUploadService extends IService<FileUpload> {
    
    /**
     * 根据文件MD5查询文件
     *
     * @param fileMd5 文件MD5值
     * @return 文件信息
     */
    FileUpload getByFileMd5(String fileMd5);
    
    /**
     * 更新文件上传状态
     *
     * @param id 文件ID
     * @param status 状态
     * @return 是否成功
     */
    boolean updateStatus(Long id, Integer status);
    
    /**
     * 更新已上传分片数
     *
     * @param id 文件ID
     * @return 是否成功
     */
    boolean incrementUploadedChunks(Long id);
    
    /**
     * 根据文件存储路径获取文件上传记录
     * @param filePath 文件存储路径
     * @return FileUpload 对象，如果找不到则返回 null
     */
    FileUpload getByFilePath(String filePath);
} 