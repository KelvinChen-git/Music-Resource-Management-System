package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.mpatric.mp3agic.ID3v2;
import com.mpatric.mp3agic.Mp3File;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.MusicCategory;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.domain.RecycleBinSettings;
import com.taffy.music.domain.MusicTags;
import com.taffy.music.mapper.MusicResourceMapper;
import com.taffy.music.service.FileUploadService;
import com.taffy.music.service.MusicCategoryService;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.RecycleBinService;
import com.taffy.music.service.RecycleBinSettingsService;
import com.taffy.music.service.UserService;
import com.taffy.music.service.MusicTagService;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.MusicMetadataVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.context.annotation.Lazy;

import java.io.File;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
public class MusicResourceServiceImpl extends ServiceImpl<MusicResourceMapper, MusicResources> implements MusicResourceService {

    @Autowired
    private MusicCategoryService musicCategoryService;

    @Autowired
    private FileUploadService fileUploadService;

    @Lazy
    @Autowired
    private UserService userService;

    @Lazy
    @Autowired
    private RecycleBinService recycleBinService;

    @Autowired
    private RecycleBinSettingsService recycleBinSettingsService;

    @Autowired
    private MusicTagService musicTagService;

    @Value("${upload.path}")
    private String uploadPath;

    @Override
    public Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, Boolean onlyMine, Integer current, Integer pageSize, List<Long> tagIds, String keyword) {
        // Calls the most comprehensive overload with nulls for other filters
        return getMusicResourceList(title, artist, album, categoryId, onlyMine, current, pageSize, null, null, null, "uploadTime", "desc", tagIds, null, null, keyword);
    }

    @Override
    public Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, List<Long> tagIds, String keyword) {
        // Calls the most comprehensive overload with null for approvalStatus
        return getMusicResourceList(title, artist, album, categoryId, onlyMine, current, pageSize, userIdByName, userIdByEmail, null, "uploadTime", "desc", tagIds, null, null, keyword);
    }

    @Override
    public Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, String approvalStatus, List<Long> tagIds, String keyword) {
         // Calls the most comprehensive overload with default sorting
        return getMusicResourceList(title, artist, album, categoryId, onlyMine, current, pageSize, userIdByName, userIdByEmail, approvalStatus, "uploadTime", "desc", tagIds, null, null, keyword);
    }

    public Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, String approvalStatus, String orderBy, String orderType, List<Long> tagIds, String keyword) {
        Page<MusicResources> page = new Page<>(current, pageSize);
        LambdaQueryWrapper<MusicResources> wrapper = new LambdaQueryWrapper<>();
        // Apply basic filters
        wrapper.like(StringUtils.hasText(title), MusicResources::getTitle, title);
        wrapper.like(StringUtils.hasText(artist), MusicResources::getArtist, artist);
        wrapper.like(StringUtils.hasText(album), MusicResources::getAlbum, album);
        wrapper.eq(categoryId != null, MusicResources::getCategoryid, categoryId);
        wrapper.eq(StringUtils.hasText(approvalStatus), MusicResources::getApprovalStatus, approvalStatus);
        
        // Apply user filter
        if (onlyMine != null && onlyMine) {
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId != null) {
                wrapper.eq(MusicResources::getUserid, currentUserId);
            } else {
                return new Page<>(current, pageSize); // Return empty if user not found but onlyMine requested
            }
        } else {
            if (userIdByName != null) {
                wrapper.eq(MusicResources::getUserid, userIdByName);
            } else if (userIdByEmail != null) {
                wrapper.eq(MusicResources::getUserid, userIdByEmail);
            }
        }
        
        // Exclude deleted
        wrapper.eq(MusicResources::getIsDeleted, false);
        
        // === Add Tag Filter Logic ===
        if (tagIds != null && !tagIds.isEmpty()) {
            List<Long> musicIds = baseMapper.findMusicIdsByTagIds(tagIds);
            if (musicIds.isEmpty()) {
                return new Page<>(current, pageSize); // No music found for these tags
            }
            wrapper.in(MusicResources::getMusicid, musicIds);
        }
        // ============================

        // Apply sorting
        boolean isAsc = "asc".equalsIgnoreCase(orderType);
        if ("title".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getTitle);
        } else if ("artist".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getArtist);
        } else if ("album".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getAlbum);
        } else if ("genre".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getGenre);
        } else if ("playCount".equalsIgnoreCase(orderBy) || "play_count".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getPlayCount);
        } else if ("fileSize".equalsIgnoreCase(orderBy) || "file_size".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getFileSize);
        } else if ("approvalStatus".equalsIgnoreCase(orderBy) || "approval_status".equalsIgnoreCase(orderBy)) {
            wrapper.orderBy(true, isAsc, MusicResources::getApprovalStatus);
        } else { // Default sort by uploadTime
            wrapper.orderBy(true, isAsc, MusicResources::getUploadTime);
        }

        // CHECKLIST 12: 添加 keyword 模糊搜索逻辑
        if (StringUtils.hasText(keyword)) {
            wrapper.and(nestedWrapper -> nestedWrapper
                .like(MusicResources::getAdditionalMetadata, keyword).or()
                .like(MusicResources::getAlbum, keyword).or()
                .like(MusicResources::getApprovalStatus, keyword).or()
                .like(MusicResources::getArtist, keyword).or()
                .like(MusicResources::getGenre, keyword)
            );
        }

        Page<MusicResources> resultPage = page(page, wrapper);
        // Populate category names
        if (resultPage.getRecords() != null && !resultPage.getRecords().isEmpty()) {
            for (MusicResources music : resultPage.getRecords()) {
                if (music.getCategoryid() != null) {
                    MusicCategory category = musicCategoryService.getById(music.getCategoryid());
                    if (category != null) {
                        music.setCategoryName(category.getCategoryName());
                    }
                }
            }
        }
        return resultPage;
    }

    @Override
    public Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, 
            Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize, List<Long> tagIds, String keyword) {
         // Calls the most comprehensive overload with nulls/defaults
        return getMusicResourceListWithDeletedOption(title, artist, album, categoryId, onlyMine, includeDeleted, current, pageSize, null, null, "uploadTime", "desc", tagIds, keyword);
    }

    @Override
    public Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, 
            Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize,
            Long userIdByName, Long userIdByEmail, List<Long> tagIds, String keyword) {
         // Calls the most comprehensive overload with default sorting
        return getMusicResourceListWithDeletedOption(title, artist, album, categoryId, onlyMine, includeDeleted, current, pageSize, userIdByName, userIdByEmail, "uploadTime", "desc", tagIds, keyword);
    }

    @Override
    public Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize, Long userIdByName, Long userIdByEmail, String orderBy, String orderType, List<Long> tagIds, String keyword) {
        // Always use the custom query, pass keyword if present
        Page<MusicResources> page = new Page<>(current, pageSize);
        Map<String, Object> params = new HashMap<>();
        
        if (StringUtils.hasText(keyword)) {
            params.put("keywordParam", "%" + keyword + "%");
        }
        // Add all other parameters
        params.put("title", title);
        params.put("artist", artist);
        params.put("album", album);
        params.put("categoryId", categoryId);
        params.put("onlyMine", onlyMine);
        params.put("currentUserId", UserContext.getCurrentUserId());
        params.put("userIdByName", userIdByName);
        params.put("userIdByEmail", userIdByEmail);
        params.put("tagIds", tagIds);
        params.put("orderBy", orderBy);
        params.put("orderType", orderType);
        params.put("includeDeleted", includeDeleted); // Pass the actual includeDeleted value
        
        return baseMapper.selectMusicPageWithComplexFilters(page, params);
    }

    @Override
    public MusicResources getMusicResourceById(Integer id) {
        MusicResources music = getById(id);
        if (music != null && music.getCategoryid() != null) {
            MusicCategory category = musicCategoryService.getById(music.getCategoryid());
            if (category != null) {
                music.setCategoryName(category.getCategoryName());
            }
        }
        return music;
    }

    @Override
    @Transactional
    public boolean updateMusicResource(Long id, MusicMetadataVO metadata) {
        // 检查资源是否存在
        MusicResources music = getById(id);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }

        // PLAN CHECK: Add check for associated FileUpload record status
        String filePath = music.getFilePath();
        if (StringUtils.hasText(filePath)) {
            FileUpload fileUploadRecord = fileUploadService.getByFilePath(filePath);
            if (fileUploadRecord == null) {
                throw new RuntimeException("关联的原始上传文件记录不存在，无法更新。");
            }
            if (Boolean.TRUE.equals(fileUploadRecord.getDeleted())) {
                throw new RuntimeException("关联的原始上传文件已被删除，无法更新。");
            }
        } else {
            // Optional: Log a warning or decide if update is allowed if filePath is missing
            log.warn("MusicResource (ID: {}) is missing filePath, cannot verify original upload status. Proceeding with metadata update.", id);
        }

        // 检查分类是否存在
        if (metadata.getCategoryId() != null) {
            MusicCategory category = musicCategoryService.getById(metadata.getCategoryId());
            if (category == null) {
                throw new RuntimeException("所选分类不存在");
            }
            music.setCategoryid(metadata.getCategoryId().longValue());
        }

        // 更新资源信息
        music.setTitle(metadata.getTitle());
        music.setArtist(metadata.getArtist());
        music.setAlbum(metadata.getAlbum());
        music.setGenre(metadata.getGenre());
        
        // 先更新音乐资源本身
        boolean updateSuccess = updateById(music);

        if (updateSuccess) {
            // 获取当前用户ID (需要在方法内获取，或者从安全上下文获取)
            Long currentUserId = UserContext.getCurrentUserId(); 
            if (currentUserId == null) {
                 // Handle case where user context might not be available (e.g., system process)
                 // Depending on requirements, you might log a warning, skip tag update, or throw an error.
                 log.warn("User context not available when updating music resource {}, skipping tag update.", id);
                 // Or: throw new IllegalStateException("User context required to update tags.");
            } else {
                 // 更新标签关联
                 this.updateMusicTags(id, currentUserId, metadata.getTagIds());
            }
        }

        return updateSuccess;
    }

    @Override
    @Transactional
    public MusicMetadataVO parseAndSaveMetadata(Long fileId, MusicMetadataVO metadata) {
        // 获取文件信息
        FileUpload fileUpload = fileUploadService.getById(fileId);
        if (fileUpload == null) {
            throw new RuntimeException("文件不存在");
        }

        // 检查文件状态
        if (fileUpload.getStatus() != 1) {
            throw new RuntimeException("文件未上传完成");
        }

        // 检查文件类型
        if (!"mp3".equalsIgnoreCase(fileUpload.getFileType())) {
            throw new RuntimeException("仅支持MP3文件格式");
        }

        try {
            // 构建完整的文件路径
            String fullPath = uploadPath + File.separator + fileUpload.getFilePath();
            File file = new File(fullPath);
            if (!file.exists()) {
                throw new RuntimeException("文件不存在：" + fullPath);
            }

            // 解析MP3文件元数据
            Mp3File mp3file = new Mp3File(file);
            
            // 如果没有提供元数据，尝试从文件中读取
            if (metadata == null) {
                metadata = new MusicMetadataVO();
                Map<String, Object> fullMetadata = new HashMap<>();
                
                if (mp3file.hasId3v2Tag()) {
                    ID3v2 id3v2Tag = mp3file.getId3v2Tag();
                    metadata.setTitle(id3v2Tag.getTitle());
                    metadata.setArtist(id3v2Tag.getArtist());
                    metadata.setAlbum(id3v2Tag.getAlbum());
                    metadata.setGenre(id3v2Tag.getGenreDescription());
                }
                
                // 如果文件没有元数据，使用文件名作为标题
                if (metadata.getTitle() == null || metadata.getTitle().trim().isEmpty()) {
                    String fileName = fileUpload.getFileName();
                    metadata.setTitle(fileName.substring(0, fileName.lastIndexOf('.')));
                }
                
                return metadata;
            }

            // 验证元数据
            if (metadata.getTitle() == null || metadata.getTitle().trim().isEmpty()) {
                throw new RuntimeException("标题不能为空");
            }
            if (metadata.getTitle().length() > 100) {
                throw new RuntimeException("标题长度不能超过100个字符");
            }

            // 检查分类是否存在
            if (metadata.getCategoryId() != null) {
                MusicCategory category = musicCategoryService.getById(metadata.getCategoryId());
                if (category == null) {
                    throw new RuntimeException("所选分类不存在");
                }
            }

            // 检查是否存在重复音乐
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                 throw new RuntimeException("User not logged in"); // Ensure user is logged in
            }

            LambdaQueryWrapper<MusicResources> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(MusicResources::getUserid, currentUserId) 
                  .eq(MusicResources::getTitle, metadata.getTitle())
                  .eq(MusicResources::getArtist, metadata.getArtist())
                  .eq(MusicResources::getAlbum, metadata.getAlbum())
                  .eq(MusicResources::getIsDeleted, false);
            
            if (count(wrapper) > 0) {
                throw new RuntimeException("您已上传过相同的音乐");
            }

            // 创建音乐资源记录
            MusicResources musicResource = new MusicResources();
            musicResource.setTitle(metadata.getTitle());
            musicResource.setArtist(metadata.getArtist());
            musicResource.setAlbum(metadata.getAlbum());
            musicResource.setGenre(metadata.getGenre());
            musicResource.setCategoryid(metadata.getCategoryId() != null ? metadata.getCategoryId().longValue() : null);
            musicResource.setFilePath(fileUpload.getFilePath());
            musicResource.setFileSize(fileUpload.getFileSize().intValue());
            musicResource.setFormat(fileUpload.getFileType());
            musicResource.setUploadTime(LocalDateTime.now());
            musicResource.setApprovalStatus("pending");
            musicResource.setUserid(currentUserId); // Use the fetched userId

            // 构建完整的元数据
            Map<String, Object> fullMetadata = new HashMap<>();
            if (mp3file.hasId3v2Tag()) {
                ID3v2 id3v2Tag = mp3file.getId3v2Tag();
                fullMetadata.put("year", id3v2Tag.getYear());
                fullMetadata.put("track", id3v2Tag.getTrack());
                fullMetadata.put("composer", id3v2Tag.getComposer());
                fullMetadata.put("publisher", id3v2Tag.getPublisher());
                fullMetadata.put("originalArtist", id3v2Tag.getOriginalArtist());
                fullMetadata.put("albumArtist", id3v2Tag.getAlbumArtist());
                fullMetadata.put("copyright", id3v2Tag.getCopyright());
                fullMetadata.put("url", id3v2Tag.getUrl());
                fullMetadata.put("encoder", id3v2Tag.getEncoder());
                fullMetadata.put("bpm", id3v2Tag.getBPM());
                
                // 添加音频特性
                fullMetadata.put("bitrate", mp3file.getBitrate());
                fullMetadata.put("sampleRate", mp3file.getSampleRate());
                fullMetadata.put("channels", mp3file.getChannelMode());
                fullMetadata.put("duration", mp3file.getLengthInSeconds());
                fullMetadata.put("isVbr", mp3file.isVbr());
            }
            musicResource.setAdditionalMetadata(fullMetadata);

            // 保存音乐资源
            save(musicResource);

            // 获取新创建的 musicId
            Long newMusicId = musicResource.getMusicid();
            if (newMusicId == null) {
                log.error("Failed to retrieve musicId after saving resource for fileId: {}", fileId);
                throw new RuntimeException("Failed to save music resource properly.");
            }

            // 设置初始标签关联 (需要在保存后进行，确保有 musicId)
            this.updateMusicTags(newMusicId, currentUserId, metadata.getTagIds());

            // 返回传入的 metadata (或根据需要调整返回内容)
            return metadata;
        } catch (Exception e) {
            log.error("处理音乐元数据失败 for fileId: {}", fileId, e);
            // Consider re-throwing a more specific exception if needed
            throw new RuntimeException("处理音乐元数据失败: " + e.getMessage());
        }
    }

    @Override
    @Transactional
    public boolean approveMusicResource(Integer id) {
        // 检查资源是否存在
        MusicResources music = getById(id);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
    
        // 检查权限，只有管理员可以审核
        if (!userService.isAdmin(UserContext.getCurrentUserId())) {
            throw new RuntimeException("没有审核权限");
        }
    
        // ✅ 修改逻辑：允许从任意状态修改为 approved
        String previousStatus = music.getApprovalStatus();
        music.setApprovalStatus("approved");
    
        boolean result = updateById(music);
        if (result) {
            log.info("音乐资源 [{}] 状态从 [{}] 修改为 [approved]", id, previousStatus);
        }
        return result;
    }

    @Override
    @Transactional
    public boolean rejectMusicResource(Integer id) {
        // 检查资源是否存在
        MusicResources music = getById(id);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
    
        // 检查权限，只有管理员可以拒绝
        if (!userService.isAdmin(UserContext.getCurrentUserId())) {
            throw new RuntimeException("没有拒绝权限");
        }
    
        // 获取原状态，记录日志
        String previousStatus = music.getApprovalStatus();
    
        // 更新审核状态为 'rejected'
        music.setApprovalStatus("rejected");
    
        // 保存更新
        boolean updated = updateById(music);
    
        if (updated) {
            log.info("音乐资源 [{}] 状态从 [{}] 修改为 [rejected]", id, previousStatus);
        }
    
        return updated;
    }

    @Override
    @Transactional
    public boolean moveToRecycleBin(Long id, String deleteNote) {
        // 获取当前用户ID
        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId == null) {
            throw new RuntimeException("用户未登录");
        }
        
        // 获取音乐资源
        MusicResources music = getById(id);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
        
        // 检查资源是否已在回收站中
        if (Boolean.TRUE.equals(music.getIsDeleted())) {
            throw new RuntimeException("音乐资源已在回收站中");
        }
        
        // 标记资源为已删除
        LocalDateTime now = LocalDateTime.now();
        music.setIsDeleted(true);
        music.setDeletedAt(now);
        music.setDeletedBy(currentUserId);
        
        // 设置保留期和永久删除时间
        // 获取回收站设置以确定保留天数
        RecycleBinSettings settings = recycleBinSettingsService.getSettings();
        int retentionDays = settings.getDefaultRetentionDays(); // 使用设置中的天数
        
        music.setRetentionPeriod(retentionDays);
        music.setPermanentDeleteTime(now.plusDays(retentionDays));
        
        // 更新音乐资源状态
        boolean updateResult = updateById(music);
        
        // 如果更新成功，则创建回收站记录
        if (updateResult) {
            try {
                // 调用RecycleBinService创建回收站记录
                return recycleBinService.moveToRecycleBin(id, deleteNote);
            } catch (Exception e) {
                log.error("创建回收站记录失败", e);
                throw new RuntimeException("创建回收站记录失败: " + e.getMessage());
            }
        }
        
        return updateResult;
    }
    
    @Override
    @Transactional
    public boolean restoreFromRecycleBin(Long id) {
        // 获取音乐资源
        MusicResources music = getById(id);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
        
        // 检查资源是否在回收站中
        if (!Boolean.TRUE.equals(music.getIsDeleted())) {
            throw new RuntimeException("音乐资源不在回收站中");
        }
        
        // 恢复音乐资源
        music.setIsDeleted(false);
        music.setDeletedAt(null);
        music.setDeletedBy(null);
        music.setPermanentDeleteTime(null);
        
        return updateById(music);
    }

    @Override
    public void incrementPlayCount(Long musicId) {
        baseMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper<MusicResources>()
            .eq("musicid", musicId)
            .setSql("play_count = play_count + 1"));
    }

    @Override
    @Transactional
    public void updateMusicTags(Long musicId, Long userId, List<Long> tagIds) {
        // 新增：校验标签数量
        if (tagIds != null && tagIds.size() > 3) {
            throw new IllegalArgumentException("A maximum of 3 tags can be added to each music file.");
        }
        
        // 1. Delete old associations
        baseMapper.deleteTagsByMusicId(musicId);

        // 2. Handle new associations
        if (tagIds == null || tagIds.isEmpty()) {
            log.info("No tags provided for musicId: {}", musicId);
            return; // No new tags, just return
        }

        // 3. Validate tag ownership
        // Get tags by IDs provided
        List<MusicTags> potentialTags = musicTagService.listByIds(tagIds);
        // Filter to get only tags owned by the current user
        Set<Long> validUserTagIds = potentialTags.stream()
                .filter(tag -> tag != null && tag.getUserId().equals(userId))
                .map(MusicTags::getTagId)
                .collect(Collectors.toSet());

        log.info("Updating tags for musicId: {}. Provided: {}, Valid owned: {}", musicId, tagIds.size(), validUserTagIds.size());

        // 4. Insert new associations for valid, owned tags
        for (Long tagId : validUserTagIds) {
            try {
                baseMapper.insertMusicTag(musicId, tagId);
            } catch (Exception e) {
                // Log potential errors like duplicate key if delete failed somehow
                log.error("Failed to insert tag association musicId: {}, tagId: {}. Maybe constraint violation?", musicId, tagId, e);
                // Decide whether to continue or re-throw
            }
        }
    }

    @Override
    @Transactional
    public boolean deleteMusicResourceConditionally(Long musicId, String deleteNote) {
        // 1. 获取音乐资源
        MusicResources music = this.getById(musicId);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在 (ID: " + musicId + ")");
        }

        // 2. 检查是否已在回收站
        if (Boolean.TRUE.equals(music.getIsDeleted())) {
            log.warn("音乐资源 (ID: {}) 已在回收站中，无需重复操作。", musicId);
            return false; // 或者根据业务需要返回 true 或抛异常
        }

        // 3. 检查物理文件是否存在
        String filePath = music.getFilePath();
        boolean fileExists = false;
        if (StringUtils.hasText(filePath)) {
            try {
                String fullPath = uploadPath + File.separator + filePath;
                File file = new File(fullPath);
                fileExists = file.exists() && file.isFile();
                log.info("检查文件存在性:路径={}, 存在={}", fullPath, fileExists);
            } catch (Exception e) {
                log.error("检查文件路径 {} 时出错: {}", filePath, e.getMessage(), e);
                // 文件路径检查出错，按文件不存在处理或抛出异常，这里选择按不存在处理
                fileExists = false;
            }
        } else {
            log.warn("音乐资源 (ID: {}) 的 filePath 为空。", musicId);
            fileExists = false; // filePath 为空视为文件不存在
        }

        // 4. 根据文件存在性执行操作
        if (!fileExists) {
            // 4.1 文件不存在 -> 直接删除记录
            log.warn("物理文件不存在，直接删除音乐资源记录 (ID: {})。", musicId);
            // 删除关联标签 (重要，removeById 不会自动处理多对多关联)
            try {
                 baseMapper.deleteTagsByMusicId(musicId);
                 log.info("已删除音乐资源 (ID: {}) 的关联标签。", musicId);
            } catch (Exception e) {
                 log.error("删除音乐资源 (ID: {}) 关联标签失败: {}", musicId, e.getMessage(), e);
                 // 可以选择继续删除主记录或抛出异常，这里选择继续
            }
            // 删除主记录
            boolean removed = this.removeById(musicId);
            if (!removed) {
                log.error("直接删除音乐资源记录 (ID: {}) 失败。", musicId);
                throw new RuntimeException("直接删除音乐资源记录失败");
            }
            return true; // 直接删除成功
        } else {
            // 4.2 文件存在 -> 移入回收站
            log.info("物理文件存在，将音乐资源 (ID: {}) 移入回收站。", musicId);
            return this.moveToRecycleBin(musicId, deleteNote); // 调用现有方法
        }
    }

    @Override
    public Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, String approvalStatus, 
                                             String orderBy, String orderType, List<Long> tagIds,
                                             String startDate, String endDate, String keyword) {
        // Use custom query if keyword is present
        if (StringUtils.hasText(keyword)) {
            Page<MusicResources> page = new Page<>(current, pageSize);
            Map<String, Object> params = new HashMap<>();
            params.put("keywordParam", "%" + keyword + "%");
            // Add all other parameters to the map...
            params.put("title", title);
            params.put("artist", artist);
            params.put("album", album);
            params.put("categoryId", categoryId);
            params.put("onlyMine", onlyMine);
            params.put("currentUserId", UserContext.getCurrentUserId());
            params.put("userIdByName", userIdByName);
            params.put("userIdByEmail", userIdByEmail);
            params.put("approvalStatus", approvalStatus);
            params.put("tagIds", tagIds);
            params.put("startDate", StringUtils.hasText(startDate) ? LocalDate.parse(startDate).atStartOfDay() : null);
            params.put("endDate", StringUtils.hasText(endDate) ? LocalDate.parse(endDate) : null);
            params.put("orderBy", orderBy);
            params.put("orderType", orderType);
            params.put("includeDeleted", false); 
            
            return baseMapper.selectMusicPageWithComplexFilters(page, params);
        } else {
            // If no keyword, still use the custom query but without the keyword parameter
            // This avoids duplicating the LambdaQueryWrapper logic
            Page<MusicResources> page = new Page<>(current, pageSize);
            Map<String, Object> params = new HashMap<>();
            // Add all other parameters EXCEPT keywordParam
            params.put("title", title);
            params.put("artist", artist);
            params.put("album", album);
            params.put("categoryId", categoryId);
            params.put("onlyMine", onlyMine);
            params.put("currentUserId", UserContext.getCurrentUserId());
            params.put("userIdByName", userIdByName);
            params.put("userIdByEmail", userIdByEmail);
            params.put("approvalStatus", approvalStatus);
            params.put("tagIds", tagIds);
            params.put("startDate", StringUtils.hasText(startDate) ? LocalDate.parse(startDate).atStartOfDay() : null);
            params.put("endDate", StringUtils.hasText(endDate) ? LocalDate.parse(endDate) : null);
            params.put("orderBy", orderBy);
            params.put("orderType", orderType);
            params.put("includeDeleted", false);

            return baseMapper.selectMusicPageWithComplexFilters(page, params);
        }
    }
} 