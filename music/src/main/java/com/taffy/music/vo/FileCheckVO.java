package com.taffy.music.vo;

import lombok.Data;

/**
 * 文件检查响应对象
 */
@Data
public class FileCheckVO {
    
    /**
     * 文件是否存在
     */
    private Boolean exists;
    
    /**
     * 文件ID
     */
    private Long fileId;
    
    /**
     * 文件路径
     */
    private String filePath;
} 