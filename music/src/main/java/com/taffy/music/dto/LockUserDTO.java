package com.taffy.music.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * User Lock DTO
 */
@Data
public class LockUserDTO {
    
    @NotNull(message = "User ID cannot be empty")
    private Long userId;
    
    @NotBlank(message = "Lock reason cannot be empty")
    private String reason;
} 