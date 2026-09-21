package com.taffy.music.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.annotation.Anonymous;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.UserService;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.MusicMetadataVO;
import com.taffy.music.vo.MusicResourceVO;
import com.taffy.music.vo.UserVO;
import com.taffy.music.mapper.MusicResourceMapper;

import jakarta.validation.Valid;

import com.taffy.music.common.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 音乐资源控制器
 */
@Slf4j
@RestController
@RequestMapping("/music-resources")
public class MusicResourceController {

    @Autowired
    private MusicResourceService musicResourceService;

    @Autowired
    private UserService userService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MusicResourceMapper musicResourceMapper;

    @Value("${upload.path}")
    private String uploadPath;

    /**
     * 获取音乐资源列表
     */
    @GetMapping("/list")
    public Result<Page<MusicResourceVO>> list(
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String artist,
            @RequestParam(required = false) String album,
            @RequestParam(required = false) Integer categoryId,
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String email,
            @RequestParam(required = false) String approvalStatus,
            @RequestParam(defaultValue = "true") Boolean onlyMine,
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false, defaultValue = "uploadTime") String orderBy,
            @RequestParam(required = false, defaultValue = "desc") String orderType,
            @RequestParam(required = false) List<Long> tagIds,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            @RequestParam(required = false) String keyword) {
        try {
            // 获取当前用户信息
            Long currentUserId = UserContext.getCurrentUserId();
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());
            
            // Determine the actual value for onlyMine based on admin status
            boolean effectiveOnlyMine = !isAdmin && onlyMine;
            
            // If user is not admin, they cannot filter by username, email, or approvalStatus
            String effectiveApprovalStatus = null;
            if (!isAdmin) {
                username = null;
                email = null;
                approvalStatus = null; // Non-admins cannot filter by approval status
            } else {
                effectiveApprovalStatus = approvalStatus; // Admins can use the filter
            }
            
            // 获取用户ID，用于按用户名或邮箱查询 (Admin only)
            Long userIdByName = null;
            boolean usernameSpecifiedButNotFound = false;
            if (isAdmin && StringUtils.hasText(username)) {
                Users user = userService.getUserByUsername(username);
                if (user != null) {
                    userIdByName = user.getUserid();
                } else {
                    usernameSpecifiedButNotFound = true;
                }
            }
            
            Long userIdByEmail = null;
            boolean emailSpecifiedButNotFound = false;
            if (isAdmin && StringUtils.hasText(email)) {
                Users user = userService.getUserByEmail(email);
                if (user != null) {
                    userIdByEmail = user.getUserid();
                } else {
                    emailSpecifiedButNotFound = true;
                }
            }

            // 如果指定了用户名或邮箱但未找到匹配的用户，返回空结果
            if (usernameSpecifiedButNotFound || emailSpecifiedButNotFound) {
                Page<MusicResourceVO> emptyPage = new Page<>(current, pageSize);
                emptyPage.setRecords(new ArrayList<>());
                emptyPage.setTotal(0);
                return Result.success(emptyPage);
            }
            
            // 调用 Service 层，传递所有过滤参数
            // IMPORTANT: We need to modify the service layer method signature and implementation
            Page<MusicResources> page = musicResourceService.getMusicResourceList(
                title, artist, album, categoryId, 
                effectiveOnlyMine, // Use the determined value
                current, pageSize, 
                userIdByName, userIdByEmail,
                effectiveApprovalStatus, // Pass the approval status filter
                orderBy, orderType,
                tagIds,
                startDate,
                endDate,
                keyword
            );
            
            // 转换为带用户信息的结果
            Page<MusicResourceVO> resultPage = convertToMusicResourceVO(page);
            
            return Result.success(resultPage);
        } catch (Exception e) {
            log.error("获取音乐列表失败", e);
            return Result.error("获取音乐列表失败：" + e.getMessage());
        }
    }

    /**
     * 获取音乐资源列表（包含回收站选项）
     */
    @GetMapping("/list-with-deleted")
    public Result<Page<MusicResourceVO>> listWithDeleted(
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String artist,
            @RequestParam(required = false) String album,
            @RequestParam(required = false) Integer categoryId,
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String email,
            @RequestParam(defaultValue = "true") Boolean onlyMine,
            @RequestParam(defaultValue = "false") Boolean includeDeleted,
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false, defaultValue = "uploadTime") String orderBy,
            @RequestParam(required = false, defaultValue = "desc") String orderType,
            @RequestParam(required = false) List<Long> tagIds,
            @RequestParam(required = false) String keyword) {
        try {
            // 获取当前用户信息
            Long currentUserId = UserContext.getCurrentUserId();
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());
            
            // 如果不是管理员，忽略用户名和邮箱查询条件
            if (!isAdmin) {
                username = null;
                email = null;
            }
            
            // 获取用户ID，用于按用户名或邮箱查询
            Long userIdByName = null;
            boolean usernameSpecifiedButNotFound = false;
            if (isAdmin && StringUtils.hasText(username)) {
                Users user = userService.getUserByUsername(username);
                if (user != null) {
                    userIdByName = user.getUserid();
                } else {
                    // 如果指定了用户名但找不到匹配的用户，应返回空列表
                    usernameSpecifiedButNotFound = true;
                }
            }
            
            Long userIdByEmail = null;
            boolean emailSpecifiedButNotFound = false;
            if (isAdmin && StringUtils.hasText(email)) {
                Users user = userService.getUserByEmail(email);
                if (user != null) {
                    userIdByEmail = user.getUserid();
                } else {
                    // 如果指定了邮箱但找不到匹配的用户，应返回空列表
                    emailSpecifiedButNotFound = true;
                }
            }
            
            // 如果指定了用户名或邮箱但未找到匹配的用户，返回空结果
            if (usernameSpecifiedButNotFound || emailSpecifiedButNotFound) {
                Page<MusicResourceVO> emptyPage = new Page<>(current, pageSize);
                emptyPage.setRecords(new ArrayList<>());
                emptyPage.setTotal(0);
                return Result.success(emptyPage);
            }
            
            Page<MusicResources> page = musicResourceService.getMusicResourceListWithDeletedOption(
                title, artist, album, categoryId, onlyMine, includeDeleted, current, pageSize, 
                userIdByName, userIdByEmail, orderBy, orderType, tagIds,
                keyword
            );
            
            // 转换为带用户信息的结果
            Page<MusicResourceVO> resultPage = convertToMusicResourceVO(page);
            
            return Result.success(resultPage);
        } catch (Exception e) {
            log.error("获取音乐列表失败", e);
            return Result.error("获取音乐列表失败：" + e.getMessage());
        }
    }

    /**
     * 删除音乐资源
     */
    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Integer id, @RequestParam(required = false) String deleteNote) {
        try {
            // 先查询音乐资源是否存在 (保留，以便获取 music 对象)
            MusicResources music = musicResourceService.getMusicResourceById(id);
            if (music == null || Boolean.TRUE.equals(music.getIsDeleted())) {
                return Result.error("您选择的文件不存在");
            }

            // 检查权限：仅资源所有者和管理员可以删除
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            try {
                UserVO currentUser = userService.getCurrentUserInfo();
                boolean isAdmin = "ADMIN".equals(currentUser.getRole());
                if (!isAdmin && !currentUserId.equals(music.getUserid())) {
                    return Result.error("无权删除该资源");
                }
            } catch (Exception e) {
                log.error("获取用户信息失败", e);
                return Result.error("验证权限失败");
            }

            // 调用新的条件删除服务方法
            boolean success = musicResourceService.deleteMusicResourceConditionally(music.getMusicid(), deleteNote);
            
            // 根据结果返回不同的消息 (可选)
            if (success) {
                // 这里可以进一步判断是直接删除还是移入回收站，但目前统一返回成功
                 return Result.success(true); 
            } else {
                 // 可能表示资源已在回收站或发生错误 (取决于 service 实现)
                 return Result.error("删除操作失败或资源已处理"); 
            }

        } catch (RuntimeException e) { // 捕获 Service 层可能抛出的异常
            log.error("删除音乐资源失败 (ID: {})", id, e);
            return Result.error("删除音乐资源失败：" + e.getMessage());
        } catch (Exception e) { // 捕获其他意外错误
            log.error("删除音乐资源时发生意外错误 (ID: {})", id, e);
            return Result.error("删除音乐资源时发生意外错误");
        }
    }

    /**
     * 获取音乐资源详情
     */
    @GetMapping("/{id}")
    public Result<MusicResourceVO> getById(@PathVariable Integer id) {
        try {
            MusicResources music = musicResourceService.getMusicResourceById(id);
            if (music == null) {
                return Result.error("音乐资源不存在");
            }
            
            // 检查权限：仅资源所有者和管理员可以查看详情
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            // 获取当前用户信息，检查角色
            try {
                UserVO currentUser = userService.getCurrentUserInfo();
                boolean isAdmin = "ADMIN".equals(currentUser.getRole());
                
                // 如果用户不是管理员且不是资源所有者
                if (!isAdmin && !currentUserId.equals(music.getUserid())) {
                    return Result.error("无权访问该资源");
                }
            } catch (Exception e) {
                log.error("获取用户信息失败", e);
                return Result.error("验证权限失败");
            }
            
            // 转换为VO并添加上传用户信息
            MusicResourceVO musicVO = convertToMusicResourceVO(music);
            
            return Result.success(musicVO);
        } catch (Exception e) {
            log.error("获取音乐资源失败", e);
            return Result.error("获取音乐资源失败：" + e.getMessage());
        }
    }

    /**
     * 更新音乐资源信息
     */
    @PutMapping("/{id}")
    public Result<Boolean> update(@PathVariable Long id, @Valid @RequestBody MusicMetadataVO metadata) {
        try {
            // 先查询音乐资源是否存在
            MusicResources music = musicResourceService.getMusicResourceById(id.intValue());
            if (music == null || Boolean.TRUE.equals(music.getIsDeleted())) {
                return Result.error("您选择的音乐文件不存在");
            }
            
            // 检查权限：仅资源所有者和管理员可以更新
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            // 获取当前用户信息，检查角色
            try {
                UserVO currentUser = userService.getCurrentUserInfo();
                boolean isAdmin = "ADMIN".equals(currentUser.getRole());
                
                // 如果用户不是管理员且不是资源所有者
                if (!isAdmin && !currentUserId.equals(music.getUserid())) {
                    return Result.error("无权更新该资源");
                }
            } catch (Exception e) {
                log.error("获取用户信息失败", e);
                return Result.error("验证权限失败");
            }
            
            // 执行更新操作
            boolean success = musicResourceService.updateMusicResource(id, metadata);
            return success ? Result.success(true) : Result.error("更新音乐资源失败");
        } catch (Exception e) {
            log.error("更新音乐资源失败", e);
            return Result.error("更新音乐资源失败：" + e.getMessage());
        }
    }

    /**
     * 解析并保存音乐元数据
     */
    @PostMapping("/metadata")
    public Result<MusicMetadataVO> parseMetadata(@RequestParam Long fileId, @RequestBody(required = false) MusicMetadataVO metadata) {
        try {
            // 检查用户是否登录
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            // 调用服务解析和保存元数据
            MusicMetadataVO result = musicResourceService.parseAndSaveMetadata(fileId, metadata);
            return Result.success(result);
        } catch (Exception e) {
            log.error("解析音乐元数据失败", e);
            return Result.error("解析音乐元数据失败：" + e.getMessage());
        }
    }

    /**
     * 审核音乐资源
     */
    @PostMapping("/{id}/approve")
    public Result<Boolean> approve(@PathVariable Integer id) {
        try {
            // 检查权限：只有管理员可以审核
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }
            
            // 获取当前用户信息，检查角色
            try {
                UserVO currentUser = userService.getCurrentUserInfo();
                if (!"ADMIN".equals(currentUser.getRole())) {
                    return Result.error("只有管理员可以审核音乐资源");
                }
            } catch (Exception e) {
                log.error("获取用户信息失败", e);
                return Result.error("验证权限失败");
            }
            
            // 执行审核操作
            boolean success = musicResourceService.approveMusicResource(id);
            return success ? Result.success(true) : Result.error("审核音乐资源失败");
        } catch (Exception e) {
            log.error("审核音乐资源失败", e);
            return Result.error("审核音乐资源失败：" + e.getMessage());
        }
    }

    /**
     * 拒绝音乐资源审核
     */
    @PostMapping("/{id}/reject")
    public Result<Boolean> reject(@PathVariable Integer id) {
        try {
            // 检查权限：只有管理员可以拒绝
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error(401, "Please log in first");
            }

            // 获取当前用户信息，检查角色
            try {
                UserVO currentUser = userService.getCurrentUserInfo();
                if (!"ADMIN".equals(currentUser.getRole())) {
                    return Result.error(403, "Only administrators can reject music resources");
                }
            } catch (Exception e) {
                log.error("Failed to get user info", e);
                return Result.error(500, "Permission verification failed");
            }

            // 调用Service层执行拒绝操作
            // IMPORTANT: Need to add rejectMusicResource method to the service layer
            boolean success = musicResourceService.rejectMusicResource(id);
            return success ? Result.success(true) : Result.error("Failed to reject music resource");
        } catch (Exception e) {
            log.error("Failed to reject music resource", e);
            return Result.error("Failed to reject music resource: " + e.getMessage());
        }
    }

    /**
     * 获取音乐文件
     */
    @GetMapping("/{id}/file")
    @Anonymous
    public ResponseEntity<Resource> getFile(@PathVariable Integer id, @RequestParam(required = false) String fileName, @RequestParam(required = false) String pay) {
        try {
            // 播放次数+1
            if (pay != null && ("1".equals(pay) || "true".equalsIgnoreCase(pay))) {
                musicResourceService.incrementPlayCount(id.longValue());
            }
            MusicResources music = musicResourceService.getMusicResourceById(id);
            if (music == null) {
                return ResponseEntity.notFound().build();
            }

            // 构建文件路径
            String filePath = uploadPath + File.separator + music.getFilePath();
            File file = new File(filePath);
            if (!file.exists()) {
                return ResponseEntity.notFound().build();
            }

            // 创建文件资源
            Resource resource = new FileSystemResource(file);
            
            // 如果没有提供文件名，则使用音乐标题
            if (fileName == null || fileName.trim().isEmpty()) {
                fileName = music.getTitle() + "." + music.getFormat();
            }
            
            // URL编码文件名
            String encodedFileName = URLEncoder.encode(fileName, StandardCharsets.UTF_8)
                    .replace("+", "%20");

            // 设置响应头
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("audio/mpeg"))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encodedFileName)
                    .header(HttpHeaders.ACCEPT_RANGES, "bytes")
                    .header(HttpHeaders.CACHE_CONTROL, "max-age=31536000")
                    .header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "*")
                    .header(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, "GET, HEAD")
                    .header(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, "*")
                    .header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS, "*")
                    .body(resource);
        } catch (Exception e) {
            log.error("获取音乐文件失败", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
    
    /**
     * 将 MusicResources 对象转换为包含上传用户信息的 MusicResourceVO 对象
     */
    private MusicResourceVO convertToMusicResourceVO(MusicResources music) {
        if (music == null) {
            return null;
        }
        
        MusicResourceVO vo = new MusicResourceVO();
        // 复制基本属性
        vo.setMusicid(music.getMusicid());
        vo.setUserid(music.getUserid());
        vo.setCategoryid(music.getCategoryid());
        vo.setCategoryName(music.getCategoryName());
        vo.setTitle(music.getTitle());
        vo.setArtist(music.getArtist());
        vo.setAlbum(music.getAlbum());
        vo.setGenre(music.getGenre());
        vo.setFilePath(music.getFilePath());
        vo.setFormat(music.getFormat());
        vo.setFileSize(music.getFileSize());
        vo.setUploadTime(music.getUploadTime());
        vo.setApprovalStatus(music.getApprovalStatus());
        vo.setAdditionalMetadata(music.getAdditionalMetadata());
        vo.setIsDeleted(music.getIsDeleted());
        vo.setDeletedAt(music.getDeletedAt());
        vo.setDeletedBy(music.getDeletedBy());
        vo.setRetentionPeriod(music.getRetentionPeriod());
        vo.setPermanentDeleteTime(music.getPermanentDeleteTime());
        vo.setPlayCount(music.getPlayCount());
        
        // 获取并设置上传用户信息
        if (music.getUserid() != null) {
            try {
                Users user = userService.getById(music.getUserid());
                if (user != null) {
                    UserVO userVO = new UserVO();
                    userVO.setUserid(user.getUserid());
                    userVO.setName(user.getName());
                    userVO.setEmail(user.getEmail());
                    userVO.setAvatar(user.getAvatar());
                    userVO.setRole(user.getRole());
                    
                    vo.setUploader(userVO);
                }
            } catch (Exception e) {
                log.warn("获取上传用户信息失败: {}", e.getMessage());
            }
        }

        // 新增：获取并设置标签ID列表
        if (music.getMusicid() != null) {
            try {
                List<Long> tagIds = musicResourceMapper.findTagIdsByMusicId(music.getMusicid());
                vo.setTagIds(tagIds);
            } catch (Exception e) {
                log.error("获取音乐资源 {} 的标签失败: {}", music.getMusicid(), e.getMessage());
                vo.setTagIds(new ArrayList<>()); // 出错时设置空列表
            }
        } else {
            vo.setTagIds(new ArrayList<>()); // 如果没有 musicId，设置空列表
        }
        
        return vo;
    }
    
    /**
     * 将 Page<MusicResources> 转换为 Page<MusicResourceVO>
     */
    private Page<MusicResourceVO> convertToMusicResourceVO(Page<MusicResources> page) {
        if (page == null) {
            return null;
        }
        
        // 创建新的分页对象
        Page<MusicResourceVO> voPage = new Page<>();
        voPage.setCurrent(page.getCurrent());
        voPage.setSize(page.getSize());
        voPage.setTotal(page.getTotal());
        
        // 转换记录
        List<MusicResourceVO> voList = new ArrayList<>();
        for (MusicResources music : page.getRecords()) {
            MusicResourceVO vo = convertToMusicResourceVO(music);
            if (vo != null) {
                voList.add(vo);
            }
        }
        
        voPage.setRecords(voList);
        return voPage;
    }

    /**
     * 导出当前用户的音乐资源数据
     * 允许用户下载自己上传的所有音乐的元数据
     */
    @GetMapping("/export-music-data")
    public ResponseEntity<Resource> exportMusicData() {
        try {
            // 获取当前用户ID
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                throw new RuntimeException("请先登录");
            }
            
            // 获取用户的所有音乐资源（设置较大的pageSize以获取所有数据）
            Page<MusicResources> page = musicResourceService.getMusicResourceList(
                null, null, null, null, true, 1, 1000, null, null, null, "uploadTime", "desc", null,
                null, null, null);
            
            // 确保我们有一个有效的列表
            List<MusicResources> musicList = page != null ? page.getRecords() : new ArrayList<>();
            
            // 准备导出数据
            List<Map<String, Object>> exportDataList = new ArrayList<>();
            
            for (MusicResources music : musicList) {
                if (music == null) continue; // 跳过null记录
                
                try {
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
                    
                    exportDataList.add(musicData);
                } catch (Exception e) {
                    log.warn("处理音乐数据时出错，已跳过: musicId={}, error={}", 
                        music.getMusicid(), e.getMessage());
                }
            }
            
            // 创建导出数据对象
            Map<String, Object> fullExportData = new HashMap<>();
            fullExportData.put("userId", currentUserId);
            fullExportData.put("exportTime", java.time.LocalDateTime.now().toString());
            fullExportData.put("musicResources", exportDataList);
            fullExportData.put("totalCount", exportDataList.size());
            
            // 转换为JSON
            byte[] data = objectMapper.writeValueAsBytes(fullExportData);
            
            // 设置文件名
            String filename = "user_" + currentUserId + "_music_data.json";
            
            // 设置响应头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setContentDispositionFormData("attachment", filename);
            
            // 创建资源
            ByteArrayResource resource = new ByteArrayResource(data);
            
            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(data.length)
                    .body(resource);
        } catch (Exception e) {
            log.error("导出用户音乐资源数据失败", e);
            
            try {
                // 创建错误响应
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("success", false);
                errorResponse.put("message", "导出音乐数据失败: " + e.getMessage());
                errorResponse.put("timestamp", java.time.LocalDateTime.now().toString());
                
                // 转换为JSON
                byte[] errorData = objectMapper.writeValueAsBytes(errorResponse);
                
                // 设置错误响应头
                HttpHeaders errorHeaders = new HttpHeaders();
                errorHeaders.setContentType(MediaType.APPLICATION_JSON);
                
                // 创建错误资源
                ByteArrayResource errorResource = new ByteArrayResource(errorData);
                
                // 返回带有错误信息的400响应
                return ResponseEntity.badRequest()
                        .headers(errorHeaders)
                        .contentLength(errorData.length)
                        .body(errorResource);
            } catch (Exception jsonError) {
                log.error("创建错误响应失败", jsonError);
                throw new RuntimeException("导出失败");
            }
        }
    }

    /**
     * 打包导出用户音乐文件
     * 将用户上传的所有音乐文件打包成ZIP供下载
     * @return ZIP文件的响应实体
     */
    @GetMapping("/export-music-files")
    public ResponseEntity<Resource> exportMusicFiles() {
        try {
            // 获取当前用户ID
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                throw new RuntimeException("请先登录");
            }

            // 获取用户的所有音乐资源
            Page<MusicResources> page = musicResourceService.getMusicResourceList(
                null, null, null, null, true, 1, 1000, null, null, null, "uploadTime", "desc", null,
                null, null, null);

            List<MusicResources> musicList = page.getRecords();
            if (musicList.isEmpty()) {
                // 如果没有音乐文件，返回一个空的200响应或者包含提示信息的JSON
                // 这里我们选择返回一个带有信息的错误响应，前端可以据此提示用户
                Map<String, Object> emptyResponse = new HashMap<>();
                emptyResponse.put("success", false);
                emptyResponse.put("message", "没有可导出的音乐文件");
                byte[] emptyData = objectMapper.writeValueAsBytes(emptyResponse);
                HttpHeaders emptyHeaders = new HttpHeaders();
                emptyHeaders.setContentType(MediaType.APPLICATION_JSON);
                return ResponseEntity.status(HttpStatus.OK) // 返回200 OK 但包含错误信息
                        .headers(emptyHeaders)
                        .contentLength(emptyData.length)
                        .body(new ByteArrayResource(emptyData));
            }

            // 创建临时ZIP文件
            File tempZip = File.createTempFile("music_export_" + currentUserId + "_", ".zip");

            // 创建ZIP输出流
            try (FileOutputStream fos = new FileOutputStream(tempZip);
                 ZipOutputStream zos = new ZipOutputStream(fos)) {

                // 遍历所有音乐资源，添加到ZIP中
                for (MusicResources music : musicList) {
                    // 获取文件路径
                    String filePath = uploadPath + File.separator + music.getFilePath();
                    File musicFile = new File(filePath);

                    if (musicFile.exists() && musicFile.isFile()) { // 确保文件存在且是文件
                        // 设置ZIP条目名称 (使用文件名而不是标题+格式，避免特殊字符问题)
                        // 使用 title 作为文件名，替换非法字符
                        String safeTitle = music.getTitle() != null ? music.getTitle().replaceAll("[\\\\/:*?\"<>|]", "_") : "unknown"; // Corrected regex and added null check
                        String safeFormat = music.getFormat() != null ? music.getFormat() : "bin"; // Added null check
                        String entryName = safeTitle + "." + safeFormat;


                        ZipEntry zipEntry = new ZipEntry(entryName);
                        zos.putNextEntry(zipEntry);

                        // 写入文件内容
                        try (FileInputStream fis = new FileInputStream(musicFile)) {
                            byte[] buffer = new byte[4096]; // 增加缓冲区大小
                            int length;
                            while ((length = fis.read(buffer)) > 0) {
                                zos.write(buffer, 0, length);
                            }
                        } catch (Exception e) {
                            log.warn("添加文件到ZIP失败: {} - {}", entryName, e.getMessage());
                            // 可以选择跳过此文件或抛出异常
                        }

                        zos.closeEntry();
                    } else {
                        log.warn("音乐文件不存在或不是一个文件: {}", filePath);
                    }
                }
            } // ZipOutputStream 在 try-with-resources 结束时自动关闭

            // 检查临时zip文件是否存在且有内容
             if (!tempZip.exists() || tempZip.length() == 0) {
                // 如果zip文件为空或不存在（可能所有文件都添加失败），则返回错误信息
                tempZip.delete(); // 删除空的zip文件
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("success", false);
                errorResponse.put("message", "未能成功打包任何音乐文件");
                byte[] errorData = objectMapper.writeValueAsBytes(errorResponse);
                HttpHeaders errorHeaders = new HttpHeaders();
                errorHeaders.setContentType(MediaType.APPLICATION_JSON);
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .headers(errorHeaders)
                        .contentLength(errorData.length)
                        .body(new ByteArrayResource(errorData));
            }

            // 准备响应
            ByteArrayResource resource = new ByteArrayResource(Files.readAllBytes(tempZip.toPath()));

            // 设置响应头，确保文件名被正确编码
             String zipFileName = "music_files_" + currentUserId + ".zip";
             String encodedFileName = URLEncoder.encode(zipFileName, StandardCharsets.UTF_8.toString()).replaceAll("\\+", "%20"); // Corrected encoding

            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION,
                    "attachment; filename*=UTF-8''" + encodedFileName); // 使用 RFC 5987 格式
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM); // 使用通用的二进制流类型

            // 文件传输后删除临时文件 (使用 try-finally 确保临时文件被删除)
            try {
                return ResponseEntity.ok()
                        .headers(headers)
                        .contentLength(tempZip.length())
                        .body(resource);
            } finally {
                // 确保临时文件被删除
                 if (!tempZip.delete()) {
                     log.warn("无法删除临时ZIP文件: {}", tempZip.getAbsolutePath());
                 }
            }

        } catch (Exception e) {
            log.error("导出音乐文件失败", e);
             // 返回更具体的错误信息给客户端
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", "导出音乐文件时发生内部错误: " + e.getMessage());
             try {
                 byte[] errorData = objectMapper.writeValueAsBytes(errorResponse);
                 HttpHeaders errorHeaders = new HttpHeaders();
                 errorHeaders.setContentType(MediaType.APPLICATION_JSON);
                 return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .headers(errorHeaders)
                        .contentLength(errorData.length)
                        .body(new ByteArrayResource(errorData));
             } catch (Exception jsonError) {
                 log.error("创建错误响应JSON失败", jsonError);
                  // 返回一个简单的文本错误
                 return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .contentType(MediaType.TEXT_PLAIN)
                        .body(new ByteArrayResource(("导出音乐文件时发生内部错误: " + e.getMessage()).getBytes()));
             }
        }
    }
} 