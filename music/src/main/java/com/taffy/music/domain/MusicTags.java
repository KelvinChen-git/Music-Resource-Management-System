package com.taffy.music.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "music_tags")
@TableName("music_tags")
@Data
public class MusicTags {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @TableId(value = "tagid", type = IdType.AUTO)
    @Column(name = "tagid")
    private Long tagId;

    @Column(name = "tag_name")
    @TableField("tag_name")
    private String tagName;

    @Column(name = "userid")
    @TableField("userid")
    private Long userId;
}
