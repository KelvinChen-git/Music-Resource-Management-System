package com.taffy.music.vo;

import com.taffy.music.domain.MusicResources;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.util.Map;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 音乐资源数据传输对象，包含上传用户信息
 */
@Data
@NoArgsConstructor
@EqualsAndHashCode(callSuper = false)
public class MusicResourceVO {
    
    /**
     * 主键ID
     */
    private Long musicid;
    
    /**
     * 用户ID
     */
    private Long userid;
    
    /**
     * 分类ID
     */
    private Long categoryid;
    
    /**
     * 分类名称
     */
    private String categoryName;
    
    /**
     * 标题
     */
    private String title;
    
    /**
     * 艺术家
     */
    private String artist;
    
    /**
     * 专辑
     */
    private String album;
    
    /**
     * 流派
     */
    private String genre;
    
    /**
     * 文件路径
     */
    private String filePath;
    
    /**
     * 格式
     */
    private String format;
    
    /**
     * 文件大小
     */
    private Integer fileSize;
    
    /**
     * 上传时间
     */
    private LocalDateTime uploadTime;
    
    /**
     * 审批状态
     */
    private String approvalStatus;
    
    /**
     * 附加元数据
     */
    private Map<String, Object> additionalMetadata;
    
    /**
     * 是否被删除
     */
    private Boolean isDeleted;
    
    /**
     * 删除时间
     */
    private LocalDateTime deletedAt;
    
    /**
     * 删除人ID
     */
    private Long deletedBy;
    
    /**
     * 保留天数
     */
    private Integer retentionPeriod;
    
    /**
     * 永久删除时间
     */
    private LocalDateTime permanentDeleteTime;
    
    /**
     * 上传用户信息
     */
    private UserVO uploader;
    
    /**
     * 关联的标签ID列表
     */
    private List<Long> tagIds;
    
    /**
     * 播放次数
     */
    private Integer playCount;
} 