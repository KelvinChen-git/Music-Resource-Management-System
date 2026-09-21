package com.taffy.music.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.common.Result;
import com.taffy.music.domain.Users;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.dto.LockUserDTO;
import com.taffy.music.service.UserService;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.UserVO;
import jakarta.validation.Valid;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequestMapping("/users")
public class UserController {

    private final UserService userService;
    private final ObjectMapper objectMapper;
    
    @Autowired
    private MusicResourceService musicResourceService;

    public UserController(UserService userService, ObjectMapper objectMapper) {
        this.userService = userService;
        this.objectMapper = objectMapper;
    }
    
    /**
     * Check if current user is admin
     * @return boolean indicating admin status
     */
    private boolean isAdmin() {
        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId == null) {
            return false;
        }
        
        Optional<Users> currentUser = userService.getUserById(currentUserId);
        return currentUser.isPresent() && "ADMIN".equals(currentUser.get().getRole());
    }
    
    /**
     * Check admin permission
     * @return null if user is admin, otherwise return error result
     */
    private <T> Result<T> checkAdminPermission() {
        if (!isAdmin()) {
            return Result.error(403, "Only administrators can perform this operation");
        }
        return null;
    }

    /**
     * Create a new user
     */
    @PostMapping
    public Result<Users> createUser(@RequestBody Users user) {
        // Check permission
        Result<Users> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            Users createdUser = userService.createUser(user);
            return Result.success("User created successfully", createdUser);
        } catch (Exception e) {
            return Result.error("Failed to create user: " + e.getMessage());
        }
    }

    /**
     * Get user information
     */
    @GetMapping("/{id}")
    public Result<Users> getUser(@PathVariable Long id) {
        // Check permission
        Result<Users> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            return userService.getUserById(id)
                    .map(user -> Result.success(user))
                    .orElse(Result.error(404, "User does not exist"));
        } catch (Exception e) {
            return Result.error("Failed to get user information: " + e.getMessage());
        }
    }

    /**
     * Lock user (simple lock, without reason)
     */
    @PutMapping("/{id}/lock")
    public Result<Void> lockUser(@PathVariable Long id) {
        // Check permission
        Result<Void> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            userService.lockUser(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error("Failed to lock user: " + e.getMessage());
        }
    }

    /**
     * Lock user with reason
     */
    @PutMapping("/{id}/lock-with-reason")
    public Result<Void> lockUserWithReason(@PathVariable Long id, @Valid @RequestBody LockUserDTO lockUserDTO) {
        // Check permission
        Result<Void> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        // Ensure path ID matches body ID
        if (!id.equals(lockUserDTO.getUserId())) {
            return Result.error(400, "Path parameter ID does not match user ID in request body");
        }
        
        try {
            userService.lockUserWithReason(id, lockUserDTO.getReason());
            return Result.success();
        } catch (Exception e) {
            return Result.error("Failed to lock user: " + e.getMessage());
        }
    }

    /**
     * Unlock user
     */
    @PutMapping("/{id}/unlock")
    public Result<Void> unlockUser(@PathVariable Long id) {
        // Check permission
        Result<Void> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            userService.unlockUser(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error("Failed to unlock user: " + e.getMessage());
        }
    }

    /**
     * Update user information
     */
    @PutMapping("/{id}")
    public Result<Users> updateUser(@PathVariable Long id, @RequestBody Users updatedUser) {
        // Check permission
        Result<Users> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            Users user = userService.updateUser(id, updatedUser);
            return Result.success("User information updated successfully", user);
        } catch (Exception e) {
            return Result.error("Failed to update user information: " + e.getMessage());
        }
    }

    /**
     * Delete user
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteUser(@PathVariable Long id) {
        // Check permission
        Result<Void> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            userService.deleteUser(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error("Failed to delete user: " + e.getMessage());
        }
    }
    
    /**
     * Get user detailed information (including lock status)
     */
    @GetMapping("/{id}/detail")
    public Result<UserVO> getUserDetail(@PathVariable Long id) {
        // Check permission
        Result<UserVO> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            return userService.getUserById(id)
                    .map(user -> {
                        UserVO userVO = new UserVO();
                        BeanUtils.copyProperties(user, userVO);
                        return Result.success(userVO);
                    })
                    .orElse(Result.error(404, "User does not exist"));
        } catch (Exception e) {
            return Result.error("Failed to get user details: " + e.getMessage());
        }
    }
    
    /**
     * Reset user password
     */
    @PutMapping("/{id}/reset-password")
    public Result<Void> resetPassword(@PathVariable Long id, @RequestParam String newPassword) {
        // Check permission
        Result<Void> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            // Use the dedicated service method to reset password
            boolean success = userService.resetUserPassword(id, newPassword);
            if (success) {
                return Result.success();
            } else {
                return Result.error("Failed to reset password");
            }
        } catch (Exception e) {
            return Result.error("Failed to reset password: " + e.getMessage());
        }
    }
    
    /**
     * Get all users with pagination and search filters
     * @param current current page number (default 1)
     * @param size page size (default 10)
     * @param username filter by username (optional)
     * @param email filter by email (optional)
     * @param role filter by role (optional)
     * @param locked filter by lock status (optional)
     * @return paginated list of users
     */
    @GetMapping
    public Result<Page<Users>> getAllUsers(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String email,
            @RequestParam(required = false) String role,
            @RequestParam(required = false) Boolean locked
    ) {
        // Check permission
        Result<Page<Users>> permissionCheck = checkAdminPermission();
        if (permissionCheck != null) {
            return permissionCheck;
        }
        
        try {
            // Create pagination object
            Page<Users> page = new Page<>(current, size);
            
            // Create query wrapper with conditions
            LambdaQueryWrapper<Users> queryWrapper = new LambdaQueryWrapper<>();
            
            // Add filter conditions if provided
            if (StringUtils.hasText(username)) {
                queryWrapper.like(Users::getName, username);
            }
            
            if (StringUtils.hasText(email)) {
                queryWrapper.like(Users::getEmail, email);
            }
            
            if (StringUtils.hasText(role)) {
                queryWrapper.eq(Users::getRole, role);
            }
            
            if (locked != null) {
                queryWrapper.eq(Users::getIsLocked, locked);
            }
            
            // Add default sort by creation time desc
            queryWrapper.orderByDesc(Users::getCreatedAt);
            
            // Execute paginated query
            Page<Users> userPage = userService.page(page, queryWrapper);
            
            return Result.success(userPage);
        } catch (Exception e) {
            return Result.error("Failed to retrieve user list: " + e.getMessage());
        }
    }
    
    /**
     * 导出当前用户的账户数据
     * 允许用户下载自己的账户数据，包括个人信息
     */
    @GetMapping("/export-account-data")
    public ResponseEntity<Resource> exportAccountData() {
        try {
            // 获取当前用户ID和信息
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                throw new RuntimeException("请先登录");
            }
            
            // 获取用户数据
            Optional<Users> userOpt = userService.getUserById(currentUserId);
            if (userOpt.isEmpty()) {
                throw new RuntimeException("用户不存在");
            }
            
            Users user = userOpt.get();
            
            // 创建导出数据对象（排除敏感信息如密码）
            Map<String, Object> exportData = new HashMap<>();
            exportData.put("userId", user.getUserid());
            exportData.put("username", user.getName());
            exportData.put("email", user.getEmail());
            exportData.put("createdAt", user.getCreatedAt());
            exportData.put("updatedAt", user.getUpdatedAt());
            exportData.put("role", user.getRole());
            exportData.put("status", user.getIsLocked() ? "锁定" : "正常");
            
            // 转换为JSON
            byte[] data = objectMapper.writeValueAsBytes(exportData);
            
            // 文件名
            String filename = "user_" + currentUserId + "_account_data.json";
            
            // 设置响应头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setContentDispositionFormData("attachment", filename);
            
            // 创建资源并返回
            ByteArrayResource resource = new ByteArrayResource(data);
            
            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(data.length)
                    .body(resource);
        } catch (Exception e) {
            log.error("导出用户账户数据失败", e);
            throw new RuntimeException("导出用户账户数据失败: " + e.getMessage());
        }
    }
    
    /**
     * 用户删除自己的账户
     * 允许用户删除自己的账户和相关数据
     */
    @DeleteMapping("/delete-account")
    public Result<String> deleteOwnAccount() {
        try {
            // 获取当前用户ID
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            // 执行账户删除操作
            userService.deleteUser(currentUserId);
            
            return Result.success("账户已成功删除");
        } catch (Exception e) {
            log.error("删除用户账户失败", e);
            return Result.error("删除用户账户失败: " + e.getMessage());
        }
    }
    
    /**
     * 导出所有个人数据（包括账户和音乐资源数据）
     * 允许用户一次下载所有个人数据
     */
    @GetMapping("/export-all-data")
    public ResponseEntity<Resource> exportAllData() {
        try {
            // 获取当前用户ID和信息
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                throw new RuntimeException("请先登录");
            }
            
            // 获取用户账户数据
            Optional<Users> userOpt = userService.getUserById(currentUserId);
            if (userOpt.isEmpty()) {
                throw new RuntimeException("用户不存在");
            }
            
            Users user = userOpt.get();
            
            // 创建账户导出数据（排除敏感信息如密码）
            Map<String, Object> accountData = new HashMap<>();
            accountData.put("userId", user.getUserid());
            accountData.put("username", user.getName());
            accountData.put("email", user.getEmail());
            accountData.put("createdAt", user.getCreatedAt());
            accountData.put("updatedAt", user.getUpdatedAt());
            accountData.put("role", user.getRole());
            accountData.put("status", user.getIsLocked() ? "锁定" : "正常");
            
            // 获取用户的所有音乐资源
            Page<MusicResources> page = musicResourceService.getMusicResourceList(
                null, // title
                null, // artist
                null, // album
                null, // categoryId
                true, // onlyMine
                1,    // current
                1000, // pageSize
                null, // userIdByName
                null, // userIdByEmail
                null, // approvalStatus
                "uploadTime", // orderBy (default)
                "desc", // orderType (default)
                null,  // tagIds
                null, // startDate - Added null
                null,  // endDate - Added null
                null   // CHECKLIST 1: Add null for keyword parameter
            );
            
            List<MusicResources> musicList = page.getRecords();
            
            // 准备音乐导出数据
            List<Map<String, Object>> musicDataList = new ArrayList<>();
            
            for (MusicResources music : musicList) {
                Map<String, Object> musicData = new HashMap<>();
                musicData.put("musicId", music.getMusicid());
                musicData.put("title", music.getTitle());
                musicData.put("artist", music.getArtist());
                musicData.put("album", music.getAlbum());
                musicData.put("genre", music.getGenre());
                musicData.put("format", music.getFormat());
                musicData.put("fileSize", music.getFileSize());
                musicData.put("uploadTime", music.getUploadTime());
                musicData.put("categoryId", music.getCategoryid());
                musicData.put("categoryName", music.getCategoryName());
                musicData.put("additionalMetadata", music.getAdditionalMetadata());
                
                musicDataList.add(musicData);
            }
            
            // 创建包含所有信息的导出数据
            Map<String, Object> allData = new HashMap<>();
            allData.put("exportTime", java.time.LocalDateTime.now().toString());
            allData.put("accountData", accountData);
            allData.put("musicResources", musicDataList);
            allData.put("musicCount", musicDataList.size());
            
            // 转换为JSON
            byte[] data = objectMapper.writeValueAsBytes(allData);
            
            // 文件名
            String filename = "user_" + currentUserId + "_all_data.json";
            
            // 设置响应头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setContentDispositionFormData("attachment", filename);
            
            // 创建资源并返回
            ByteArrayResource resource = new ByteArrayResource(data);
            
            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(data.length)
                    .body(resource);
        } catch (Exception e) {
            log.error("导出用户所有数据失败", e);
            throw new RuntimeException("导出用户所有数据失败: " + e.getMessage());
        }
    }
}