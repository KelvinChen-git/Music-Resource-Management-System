package com.taffy.music.controller;

import com.taffy.music.common.Result;
import com.taffy.music.domain.RecycleBinSettings;
import com.taffy.music.service.RecycleBinSettingsService;
import com.taffy.music.service.UserService;
import com.taffy.music.utils.UserContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

@Slf4j
@RestController
@RequestMapping("/admin/recycle-bin/settings") // 将接口放在 /admin 路径下以示区分
public class RecycleBinSettingsController {

    @Autowired
    private RecycleBinSettingsService recycleBinSettingsService;

    @Autowired
    private UserService userService;

    // 辅助方法：检查是否为管理员
    private Result<?> checkAdminPermission() {
        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId == null || !userService.isAdmin(currentUserId)) {
            return Result.error(403, "Permission denied: Only administrators can manage recycle bin settings.");
        }
        return null;
    }

    /**
     * 获取回收站设置
     */
    @GetMapping
    public Result<RecycleBinSettings> getSettings() {
        Result<?> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            // 类型转换以匹配返回类型
            return Result.error(permissionCheck.getCode(), permissionCheck.getMessage());
        }

        try {
            RecycleBinSettings settings = recycleBinSettingsService.getSettings();
            return Result.success(settings);
        } catch (Exception e) {
            log.error("Failed to get recycle bin settings", e);
            return Result.error("Failed to retrieve settings: " + e.getMessage());
        }
    }

    /**
     * 更新回收站设置
     */
    @PutMapping
    public Result<RecycleBinSettings> updateSettings(@Valid @RequestBody RecycleBinSettings settings) {
        Result<?> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return Result.error(permissionCheck.getCode(), permissionCheck.getMessage());
        }

        try {
            // 可以在这里添加对 settings 内容的额外校验，例如 retentionDays > 0 等
            if (settings.getDefaultRetentionDays() <= 0) {
                return Result.error(400, "Default retention days must be positive.");
            }

            RecycleBinSettings updatedSettings = recycleBinSettingsService.updateSettings(settings);
            return Result.success("Settings updated successfully", updatedSettings);
        } catch (Exception e) {
            log.error("Failed to update recycle bin settings", e);
            return Result.error("Failed to update settings: " + e.getMessage());
        }
    }
} 