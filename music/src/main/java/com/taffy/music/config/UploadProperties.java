package com.taffy.music.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

/**
 * 文件上传配置属性
 */
@Data
@Component
@ConfigurationProperties(prefix = "upload")
public class UploadProperties {
    
    /**
     * 文件存储路径
     */
    private String path;
    
    /**
     * 分片大小（字节）
     */
    private Long chunkSize = 5 * 1024 * 1024L;
    
    /**
     * 允许的文件类型
     */
    private String allowedTypes;
    
    /**
     * 临时文件目录
     */
    private String tempPath;
    
    /**
     * 上传速率限制（字节/秒），默认 10MB/s
     */
    private Long uploadRateLimit = 10 * 1024 * 1024L;
    
    /**
     * 下载速率限制（字节/秒），默认 10MB/s
     */
    private Long downloadRateLimit = 10 * 1024 * 1024L;
    
    /**
     * 获取允许的文件类型列表
     */
    public List<String> getAllowedTypeList() {
        return Arrays.asList(allowedTypes.split(","));
    }
} 