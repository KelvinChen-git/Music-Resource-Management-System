package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 文件上传实体类
 */
@Data
@TableName("file_upload")
public class FileUpload {
    
    /**
     * 主键ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    
    /**
     * 文件名
     */
    @TableField("file_name")
    private String fileName;
    
    /**
     * 文件大小(字节)
     */
    @TableField("file_size")
    private Long fileSize;
    
    /**
     * 文件MD5值
     */
    @TableField("file_md5")
    private String fileMd5;
    
    /**
     * 文件存储路径
     */
    @TableField("file_path")
    private String filePath;
    
    /**
     * 文件类型
     */
    @TableField("file_type")
    private String fileType;
    
    /**
     * 分片大小(字节)
     */
    @TableField("chunk_size")
    private Integer chunkSize;
    
    /**
     * 总分片数
     */
    @TableField("chunk_count")
    private Integer chunkCount;
    
    /**
     * 已上传分片数
     */
    @TableField("uploaded_chunks")
    private Integer uploadedChunks;
    
    /**
     * 状态：0-上传中，1-上传完成，2-上传失败
     */
    @TableField("status")
    private Integer status;
    
    /**
     * 上传时间
     */
    @TableField("upload_time")
    private LocalDateTime uploadTime;
    
    /**
     * 完成时间
     */
    @TableField("complete_time")
    private LocalDateTime completeTime;
    
    /**
     * 创建时间
     */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    
    /**
     * 更新时间
     */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
    
    /**
     * 是否删除
     */
    @TableLogic
    @TableField("deleted")
    private Boolean deleted;
} 