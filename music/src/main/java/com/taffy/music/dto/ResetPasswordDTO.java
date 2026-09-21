package com.taffy.music.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Reset Password Request DTO
 */
@Data
public class ResetPasswordDTO {

    @NotBlank(message = "Email cannot be blank")
    @Email(message = "Invalid email format")
    private String email;

    @NotBlank(message = "Verification code cannot be blank")
    @Size(min = 6, max = 6, message = "Verification code must be 6 digits")
    private String code;

    @NotBlank(message = "New password cannot be blank")
    @Size(min = 6, max = 20, message = "Password length must be between 6 and 20 characters")
    private String newPassword;

    @NotBlank(message = "Confirm password cannot be blank")
    private String confirmPassword;

    // You might add a custom class-level validator later 
    // to ensure newPassword and confirmPassword match.
} 