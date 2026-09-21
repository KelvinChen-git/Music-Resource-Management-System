package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 文件分片实体类
 */
@Data
@TableName("file_chunk")
public class FileChunk {
    
    /**
     * 主键ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    
    /**
     * 文件ID
     */
    @TableField("file_id")
    private Long fileId;
    
    /**
     * 分片索引
     */
    @TableField("chunk_index")
    private Integer chunkIndex;
    
    /**
     * 分片大小(字节)
     */
    @TableField("chunk_size")
    private Integer chunkSize;
    
    /**
     * 分片存储路径
     */
    @TableField("chunk_path")
    private String chunkPath;
    
    /**
     * 分片MD5值
     */
    @TableField("chunk_md5")
    private String chunkMd5;
    
    /**
     * 状态：0-未上传，1-已上传
     */
    @TableField("status")
    private Integer status;
    
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