package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonBackReference;
import com.fasterxml.jackson.annotation.JsonIdentityInfo;
import com.fasterxml.jackson.annotation.JsonManagedReference;
import com.fasterxml.jackson.annotation.ObjectIdGenerators;
import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Entity
@Data
@Table(name = "recycle_bin")
@TableName("recycle_bin")
@JsonIdentityInfo(generator = ObjectIdGenerators.PropertyGenerator.class, property = "recycleid")
public class RecycleBin {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "recycleid")
    @TableId(value = "recycleid", type = IdType.AUTO)
    private Long recycleid;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "musicid", insertable = false, updatable = false)
    @TableField(exist = false)
    private MusicResources music;
    
    @Column(name = "musicid", nullable = false)
    @TableField("musicid")
    private Long musicid;

    @Column(name = "deleted_at", nullable = false)
    @TableField("deleted_at")
    private LocalDateTime deletedAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "deleted_by", insertable = false, updatable = false)
    @TableField(exist = false)
    private Users deletedBy;
    
    @Column(name = "deleted_by", nullable = false)
    @TableField("deleted_by") 
    private Long deletedById;

    @Column(name = "recovery_status")
    @TableField("recovery_status")
    private Boolean recoveryStatus = false;
    
    @Column(name = "permanently_deleted")
    @TableField("permanently_deleted")
    private Boolean permanentlyDeleted = false;
    
    @Column(name = "permanent_delete_time")
    @TableField("permanent_delete_time")
    private LocalDateTime permanentDeleteTime;
    
    @Column(name = "retention_period")
    @TableField("retention_period")
    private Integer retentionPeriod = 30;
    
    @Column(name = "deleted_note")
    @TableField("deleted_note")
    private String deletedNote;
}