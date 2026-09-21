package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "music_categories")
@TableName("music_categories")
public class MusicCategory {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @TableId(value = "categoryid", type = IdType.AUTO)
    @Column(name = "categoryid")
    private Integer categoryId;
    
    @Column(name = "category_name", unique = true)
    @TableField("category_name")
    private String categoryName;
    
    @Column(name = "description")
    @TableField("description")
    private String description;
} 