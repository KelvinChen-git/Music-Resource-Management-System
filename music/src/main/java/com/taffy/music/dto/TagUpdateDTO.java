package com.taffy.music.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 更新标签的数据传输对象
 */
@Data
public class TagUpdateDTO {

    @NotBlank(message = "Tag name cannot be empty")
    @Size(max = 50, message = "Tag name cannot exceed 50 characters")
    private String tagName;
} 