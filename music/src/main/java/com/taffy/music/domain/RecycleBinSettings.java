package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;
import java.time.LocalTime;

/**
 * 回收站设置实体类
 */
@Entity
@Data
@Table(name = "recycle_bin_settings")
@TableName("recycle_bin_settings")
public class RecycleBinSettings {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    
    @Column(name = "default_retention_days")
    @TableField("default_retention_days")
    private Integer defaultRetentionDays = 30;
    
    @Column(name = "auto_cleanup_enabled")
    @TableField("auto_cleanup_enabled")
    private Boolean autoCleanupEnabled = true;
    
    @Column(name = "auto_cleanup_time")
    @TableField("auto_cleanup_time")
    private LocalTime autoCleanupTime = LocalTime.of(3, 0); // 默认凌晨3点执行清理
    
    @Column(name = "create_time", insertable = false, updatable = false)
    @TableField(value = "create_time", fill = com.baomidou.mybatisplus.annotation.FieldFill.INSERT)
    private LocalDateTime createTime;
    
    @Column(name = "update_time", insertable = false, updatable = false)
    @TableField(value = "update_time", fill = com.baomidou.mybatisplus.annotation.FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
} 