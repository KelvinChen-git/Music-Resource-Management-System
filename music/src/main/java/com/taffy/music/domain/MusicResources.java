package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.annotation.JsonIdentityInfo;
import com.fasterxml.jackson.annotation.ObjectIdGenerators;
import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.Type;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Entity
@Table(name = "music_resources")
@TableName(value = "music_resources", autoResultMap = true)
@JsonIdentityInfo(generator = ObjectIdGenerators.PropertyGenerator.class, property = "musicid")
public class MusicResources {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @TableId(value = "musicid", type = IdType.AUTO)
    @Column(name = "musicid")
    private Long musicid;
    
    @Column(name = "userid")
    @TableField("userid")
    private Long userid;
    
    @Column(name = "categoryid")
    @TableField("categoryid")
    private Long categoryid;
    
    @Transient
    @TableField(exist = false)
    private String categoryName;
    
    @Column(name = "title")
    @TableField("title")
    private String title;
    
    @Column(name = "artist")
    @TableField("artist")
    private String artist;
    
    @Column(name = "album")
    @TableField("album")
    private String album;
    
    @Column(name = "genre")
    @TableField("genre")
    private String genre;
    
    @Column(name = "file_path")
    @TableField("file_path")
    private String filePath;
    
    @Column(name = "format")
    @TableField("format")
    private String format;
    
    @Column(name = "file_size")
    @TableField("file_size")
    private Integer fileSize;
    
    @Column(name = "upload_time")
    @TableField("upload_time")
    private LocalDateTime uploadTime;
    
    @Column(name = "approval_status")
    @TableField("approval_status")
    private String approvalStatus;
    
    @Column(name = "additional_metadata", columnDefinition = "json")
    @JdbcTypeCode(SqlTypes.JSON)
    @TableField(value = "additional_metadata", typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> additionalMetadata;
    
    @Column(name = "is_deleted")
    @TableField("is_deleted")
    private Boolean isDeleted = false;
    
    @Column(name = "deleted_at")
    @TableField("deleted_at")
    private LocalDateTime deletedAt;
    
    @Column(name = "deleted_by")
    @TableField("deleted_by")
    private Long deletedBy;
    
    @Column(name = "retention_period")
    @TableField("retention_period")
    private Integer retentionPeriod = 30;
    
    @Column(name = "permanent_delete_time")
    @TableField("permanent_delete_time")
    private LocalDateTime permanentDeleteTime;
    
    @Column(name = "play_count")
    @TableField("play_count")
    private Integer playCount = 0;
}