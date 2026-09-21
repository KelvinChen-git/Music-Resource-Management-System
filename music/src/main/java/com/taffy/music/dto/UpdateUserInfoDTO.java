package com.taffy.music.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 更新用户信息DTO
 */
@Data
public class UpdateUserInfoDTO {
    
    @Size(min = 2, max = 20, message = "用户名长度必须在2-20个字符之间")
    private String name;
    
    private String avatar;
} 