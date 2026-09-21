package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.*;
import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import com.fasterxml.jackson.annotation.JsonIdentityInfo;
import com.fasterxml.jackson.annotation.ObjectIdGenerators;

@Data
@Entity
@Table(name = "users")
@TableName("users")
@JsonIdentityInfo(generator = ObjectIdGenerators.PropertyGenerator.class, property = "userid")
public class Users {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @TableId(value = "userid", type = IdType.AUTO)
    @Column(name = "userid")
    private Long userid;
    
    @Column(name = "name")
    @TableField("name")
    private String name;
    
    @Column(name = "email")
    @TableField("email")
    private String email;
    
    @Column(name = "avatar")
    @TableField("avatar")
    private String avatar;
    
    @Column(name = "password")
    @TableField("password")
    private String password;
    
    @Column(name = "role")
    @TableField("role")
    private String role;
    
    @Column(name = "verification_status")
    @TableField("verification_status")
    private Boolean verificationStatus;
    
    @Column(name = "is_locked")
    @TableField("is_locked")
    private Boolean isLocked;
    
    @Column(name = "lock_reason")
    @TableField("lock_reason")
    private String lockReason;
    
    @Column(name = "lock_time")
    @TableField("lock_time")
    private LocalDateTime lockTime;
    
    @Column(name = "unlock_time")
    @TableField("unlock_time")
    private LocalDateTime unlockTime;
    
    @Column(name = "created_at")
    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}