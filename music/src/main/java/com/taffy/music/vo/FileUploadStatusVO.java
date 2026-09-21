package com.taffy.music.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 文件上传状态VO
 */
@Data
public class FileUploadStatusVO {
    /**
     * 文件ID
     */
    private Long fileId;
    
    /**
     * 文件名
     */
    private String fileName;
    
    /**
     * 文件大小
     */
    private Long fileSize;
    
    /**
     * 文件类型
     */
    private String fileType;
    
    /**
     * 总分片数
     */
    private Integer chunkCount;
    
    /**
     * 已上传分片数
     */
    private Integer uploadedChunks;
    
    /**
     * 上传状态：0-上传中，1-已完成
     */
    private Integer status;
    
    /**
     * 上传进度（百分比）
     */
    private Integer progress;
    
    /**
     * 已上传的分片索引列表
     */
    private List<Integer> uploadedChunkIndexes;
    
    /**
     * 缺失的分片索引列表
     */
    private List<Integer> missingChunkIndexes;
    
    /**
     * 开始上传时间
     */
    private LocalDateTime createTime;
    
    /**
     * 最后更新时间
     */
    private LocalDateTime updateTime;
} 