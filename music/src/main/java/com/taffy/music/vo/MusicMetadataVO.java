package com.taffy.music.vo;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;
import java.util.List;

@Data
public class MusicMetadataVO {
    /**
     * 标题
     */
    @NotBlank(message = "标题不能为空")
    @Size(max = 100, message = "标题长度不能超过100个字符")
    private String title;

    /**
     * 艺术家
     */
    @Size(max = 50, message = "艺术家名称不能超过50个字符")
    private String artist;

    /**
     * 专辑
     */
    @Size(max = 50, message = "专辑名称不能超过50个字符")
    private String album;

    /**
     * 流派
     */
    @Size(max = 30, message = "流派名称不能超过30个字符")
    private String genre;

    /**
     * 分类ID
     */
    private Integer categoryId;

    private List<Long> tagIds;
} 