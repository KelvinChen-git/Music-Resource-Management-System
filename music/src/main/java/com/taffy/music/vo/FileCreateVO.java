package com.taffy.music.vo;

import lombok.Data;

/**
 * 文件创建请求参数
 */
@Data
public class FileCreateVO {
    /**
     * 文件名
     */
    private String fileName;
    
    /**
     * 文件大小（字节）
     */
    private Long fileSize;
    
    /**
     * 文件MD5
     */
    private String fileMd5;
    
    /**
     * 总分片数
     */
    private Integer chunkCount;
} 