package com.taffy.music.controller;

import com.taffy.music.common.Result;
import com.taffy.music.dto.ChangePasswordDTO;
import com.taffy.music.dto.ForgotPasswordDTO;
import com.taffy.music.dto.LoginDTO;
import com.taffy.music.dto.RegisterDTO;
import com.taffy.music.dto.ResetPasswordDTO;
import com.taffy.music.dto.UpdateUserInfoDTO;
import com.taffy.music.service.UserService;
import com.taffy.music.vo.UserVO;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/auth")
public class AuthController {
    
    @Autowired
    private UserService userService;
    
    @PostMapping("/register")
    public Result<UserVO> register(@Valid @RequestBody RegisterDTO registerDTO) {
        try {
            UserVO userVO = userService.register(registerDTO);
            return Result.success("Registration successful", userVO);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    @PostMapping("/login")
    public Result<?> login(@RequestBody LoginDTO loginDTO) {
        try {
            String token = userService.login(loginDTO);
            Map<String, String> tokenMap = new HashMap<>();
            tokenMap.put("token", token);
            return Result.success("Login successful", tokenMap);
        } catch (RuntimeException e) {
            // Check if it's an account locked exception
            if (e.getMessage() != null && e.getMessage().contains("Account is locked")) {
                return Result.error(403, e.getMessage());
            }
            return Result.error("Invalid email or password");
        }
    }
    
    /**
     * 获取当前登录用户的个人信息
     */
    @GetMapping("/profile")
    public Result<UserVO> getProfile() {
        try {
            UserVO userVO = userService.getCurrentUserInfo();
            return Result.success(userVO);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 更新当前登录用户的个人信息
     */
    @PutMapping("/profile")
    public Result<UserVO> updateProfile(@Valid @RequestBody UpdateUserInfoDTO updateUserInfoDTO) {
        try {
            UserVO userVO = userService.updateCurrentUserInfo(updateUserInfoDTO);
            return Result.success("Profile updated successfully", userVO);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 修改当前登录用户的密码
     */
    @PostMapping("/change-password")
    public Result<Object> changePassword(@Valid @RequestBody ChangePasswordDTO changePasswordDTO) {
        try {
            boolean success = userService.changePassword(changePasswordDTO);
            if (success) {
                return Result.success("Password changed successfully");
            } else {
                return Result.error("Failed to change password");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    /**
     * Request password reset code.
     */
    @PostMapping("/forgot-password")
    public Result<Object> forgotPassword(@Valid @RequestBody ForgotPasswordDTO forgotPasswordDTO) {
        try {
            userService.sendPasswordResetCode(forgotPasswordDTO.getEmail());
            // Always return success to prevent email enumeration attacks
            return Result.success("If the email address exists in our system, a password reset code has been sent.");
        } catch (Exception e) {
            // Log the error, but still return a generic success message to the user
            // logger.error("Error sending password reset code for email {}: {}", forgotPasswordDTO.getEmail(), e.getMessage());
            return Result.success("If the email address exists in our system, a password reset code has been sent.");
        }
    }

    /**
     * Reset password using verification code.
     */
    @PostMapping("/reset-password")
    public Result<Object> resetPassword(@Valid @RequestBody ResetPasswordDTO resetPasswordDTO) {
        try {
            boolean success = userService.resetPassword(resetPasswordDTO);
            if (success) {
                return Result.success("Password has been reset successfully.");
            } else {
                // This path might not be reached if service throws exceptions for failures
                return Result.error("Failed to reset password."); 
            }
        } catch (Exception e) {
            // Catch specific exceptions from the service if needed for different error messages
            return Result.error(e.getMessage());
        }
    }
} 