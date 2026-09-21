package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.RecycleBinMapper;
import com.taffy.music.repositories.RecycleBinRepository;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.RecycleBinService;
import com.taffy.music.service.UserService;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.RecycleBinStatsVO;
import com.taffy.music.mapper.MusicResourceMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.context.annotation.Lazy;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
public class RecycleBinServiceImpl extends ServiceImpl<RecycleBinMapper, RecycleBin> implements RecycleBinService {

    @Lazy
    @Autowired
    private MusicResourceService musicResourceService;
    
    @Lazy
    @Autowired
    private UserService userService;
    
    @Autowired
    private RecycleBinRepository recycleBinRepository;

    @Autowired
    private MusicResourceMapper musicResourceMapper;

    @Value("${upload.path}")
    private String uploadPath;

    @Override
    @Deprecated
    public Page<RecycleBin> getRecycleBinList(String title, String artist, Integer current, Integer pageSize) {
        // 调用新方法，不进行用户ID过滤
        return getRecycleBinList(title, artist, current, pageSize, null);
    }

    @Override
    public Page<RecycleBin> getRecycleBinList(String title, String artist, Integer current, Integer pageSize, Long userId) {
        Page<RecycleBin> page = new Page<>(current, pageSize);
        
        LambdaQueryWrapper<RecycleBin> wrapper = new LambdaQueryWrapper<>();
        
        // 配置JOIN查询，只查询未恢复且未永久删除的记录
        wrapper.eq(RecycleBin::getRecoveryStatus, false)
               .eq(RecycleBin::getPermanentlyDeleted, false);
        
        // 根据用户ID过滤
        if (userId != null) {
            wrapper.eq(RecycleBin::getDeletedById, userId);
        }
        
        // 根据删除时间倒序排序
        wrapper.orderByDesc(RecycleBin::getDeletedAt);
        
        // 执行分页查询
        Page<RecycleBin> resultPage = page(page, wrapper);
        
        // 手动加载关联的音乐和用户信息
        if (resultPage.getRecords() != null && !resultPage.getRecords().isEmpty()) {
            for (RecycleBin recycleBin : resultPage.getRecords()) {
                try {
                    // 加载音乐信息
                    if (recycleBin.getMusicid() != null) {
                        MusicResources music = musicResourceService.getById(recycleBin.getMusicid());
                        recycleBin.setMusic(music);
                        
                        // 如果有标题或艺术家的过滤条件，需要过滤
                        if ((StringUtils.hasText(title) && (music == null || !music.getTitle().contains(title))) ||
                            (StringUtils.hasText(artist) && (music == null || !music.getArtist().contains(artist)))) {
                            continue; // 不符合过滤条件，跳过该记录
                        }
                    }
                    
                    // 加载删除用户信息
                    if (recycleBin.getDeletedById() != null) {
                        Users deletedBy = userService.getById(recycleBin.getDeletedById());
                        recycleBin.setDeletedBy(deletedBy);
                    }
                } catch (Exception e) {
                    log.warn("加载回收站关联数据失败: {}", e.getMessage());
                }
            }
        }
        
        return resultPage;
    }

    @Override
    @Transactional
    public boolean moveToRecycleBin(Long musicId, String deleteNote) {
        // 获取当前用户
        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId == null) {
            throw new RuntimeException("用户未登录");
        }
        
        Users currentUser = userService.getById(currentUserId);
        if (currentUser == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 获取音乐资源
        MusicResources music = musicResourceService.getById(musicId);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
        
        // 注意：此处不再检查 music.getIsDeleted()，因为调用此方法前，MusicResourceServiceImpl 已经做了检查
        // 并且已经在 MusicResourceServiceImpl 中将资源标记为已删除
        
        // 创建回收站记录
        RecycleBin recycleBin = new RecycleBin();
        recycleBin.setMusicid(musicId);
        recycleBin.setDeletedAt(music.getDeletedAt()); // 使用音乐资源的删除时间
        recycleBin.setDeletedBy(currentUser);
        recycleBin.setDeletedById(currentUserId);
        recycleBin.setRecoveryStatus(false);
        recycleBin.setPermanentlyDeleted(false);
        // 使用 MusicResources 中已计算好的保留期和删除时间
        recycleBin.setRetentionPeriod(music.getRetentionPeriod());
        recycleBin.setPermanentDeleteTime(music.getPermanentDeleteTime());
        recycleBin.setDeletedNote(deleteNote);
        
        return save(recycleBin);
    }

    @Override
    @Transactional
    public MusicResources restoreFromRecycleBin(Long recycleBinId) {
        // 获取回收站记录
        RecycleBin recycleBin = getById(recycleBinId);
        if (recycleBin == null) {
            throw new RuntimeException("回收站记录不存在");
        }
        
        // 检查记录状态
        if (Boolean.TRUE.equals(recycleBin.getRecoveryStatus())) {
            throw new RuntimeException("该记录已经恢复");
        }
        
        if (Boolean.TRUE.equals(recycleBin.getPermanentlyDeleted())) {
            throw new RuntimeException("该记录已被永久删除");
        }
        
        // 获取音乐资源
        Long musicId = recycleBin.getMusicid();
        MusicResources music = musicResourceService.getById(musicId);
        if (music == null) {
            throw new RuntimeException("音乐资源不存在");
        }
        
        // 恢复音乐资源
        music.setIsDeleted(false);
        music.setDeletedAt(null);
        music.setDeletedBy(null);
        music.setPermanentDeleteTime(null);
        musicResourceService.updateById(music);
        
        // 更新回收站记录
        recycleBin.setRecoveryStatus(true);
        updateById(recycleBin);
        
        return music;
    }

    @Override
    @Transactional
    public boolean deleteFromRecycleBin(Long recycleId) {
        // 1. 获取回收站记录
        RecycleBin recycleBin = this.getById(recycleId);
        if (recycleBin == null) {
            log.warn("尝试永久删除不存在的回收站记录 (ID: {})", recycleId);
            return false; // 或者抛出异常
        }
        
        // 检查记录状态
        if (Boolean.TRUE.equals(recycleBin.getRecoveryStatus())) {
            log.warn("尝试永久删除已恢复的回收站记录 (ID: {})", recycleId);
            return false; // 或者抛出异常
        }

        if (Boolean.TRUE.equals(recycleBin.getPermanentlyDeleted())) {
            log.warn("回收站记录 (ID: {}) 已被标记为永久删除，跳过。", recycleId);
            return true; // 已经处理过，视为成功
        }
        
        Long musicId = recycleBin.getMusicid();
        if (musicId == null) {
             log.error("回收站记录 (ID: {}) 没有关联的 musicId。将仅标记回收站记录为永久删除。", recycleId);
             // 即使没有 musicId，也应该标记回收站记录本身为永久删除
             // 移除: boolean recycleRemoved = this.removeById(recycleId);
             // 移除: if (!recycleRemoved) { ... }
             // 移除: return true; // 删除了回收站记录
             // 代码将继续执行到最后的标记步骤
        }

        // 移除: 获取关联的音乐资源记录
        // 移除: MusicResources music = musicResourceService.getById(musicId);
        
        // 移除: 删除物理文件逻辑
        // 移除: if (music != null && StringUtils.hasText(music.getFilePath())) { ... } else if ... else ...

        // 移除: 删除音乐资源数据库记录逻辑 (包括标签和主记录)
        // 移除: if (music != null) { ... }

        // 5. 标记回收站记录为永久删除 (保留此部分)
        log.info("尝试标记回收站记录 (ID: {}) 为永久删除。", recycleId);
        recycleBin.setPermanentlyDeleted(true);
        recycleBin.setPermanentDeleteTime(LocalDateTime.now()); // 记录实际删除时间
        boolean recycleUpdated = this.updateById(recycleBin);

        if (!recycleUpdated) {
            log.error("标记回收站记录 (ID: {}) 为永久删除失败。", recycleId);
            // 根据业务决定是否抛异常。
            return false; 
        }
        log.info("成功标记回收站记录 (ID: {}) 为永久删除。", recycleId);

        return true; // 表示回收站记录已成功标记
    }

    @Override
    @Transactional
    public int emptyRecycleBin() {
        LambdaQueryWrapper<RecycleBin> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecycleBin::getRecoveryStatus, false)
               .eq(RecycleBin::getPermanentlyDeleted, false);
        
        List<RecycleBin> recycleBins = list(wrapper);
        int count = 0;
        
        for (RecycleBin recycleBin : recycleBins) {
            try {
                if (deleteFromRecycleBin(recycleBin.getRecycleid())) {
                    count++;
                }
            } catch (Exception e) {
                log.error("删除回收站项目失败: {}", recycleBin.getRecycleid(), e);
            }
        }
        
        return count;
    }

    @Override
    @Transactional
    public int emptyUserRecycleBin(Long userId) {
        if (userId == null) {
            log.warn("Attempted to empty recycle bin for null user ID.");
            return 0;
        }

        LambdaQueryWrapper<RecycleBin> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecycleBin::getDeletedById, userId)
               .eq(RecycleBin::getRecoveryStatus, false) // 只删除未恢复的
               .eq(RecycleBin::getPermanentlyDeleted, false); // 只删除未被永久删除的
        
        List<RecycleBin> userRecycleBins = list(wrapper);
        int count = 0;
        
        log.info("Attempting to empty recycle bin for user {}. Found {} items.", userId, userRecycleBins.size());

        for (RecycleBin recycleBin : userRecycleBins) {
            try {
                // 调用已有的单个删除逻辑，确保文件也被删除
                if (deleteFromRecycleBin(recycleBin.getRecycleid())) {
                    count++;
                }
            } catch (Exception e) {
                // 记录单个项目删除失败，但继续处理其他项目
                log.error("Failed to delete recycle bin item {} for user {}", recycleBin.getRecycleid(), userId, e);
            }
        }
        
        log.info("Successfully emptied {} recycle bin items for user {}.", count, userId);
        return count;
    }

    @Override
    public List<RecycleBin> getExpiredItems(int days) {
        LocalDateTime expiryDate = LocalDateTime.now().minusDays(days);
        
        LambdaQueryWrapper<RecycleBin> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecycleBin::getRecoveryStatus, false)
               .eq(RecycleBin::getPermanentlyDeleted, false)
               .le(RecycleBin::getDeletedAt, expiryDate);
        
        return list(wrapper);
    }

    @Override
    @Transactional
    public int autoCleanupExpiredItems() {
        LambdaQueryWrapper<RecycleBin> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RecycleBin::getRecoveryStatus, false)
               .eq(RecycleBin::getPermanentlyDeleted, false)
               .le(RecycleBin::getPermanentDeleteTime, LocalDateTime.now());
        
        List<RecycleBin> expiredItems = list(wrapper);
        int count = 0;
        
        for (RecycleBin recycleBin : expiredItems) {
            try {
                if (deleteFromRecycleBin(recycleBin.getRecycleid())) {
                    count++;
                }
            } catch (Exception e) {
                log.error("自动删除过期项目失败: {}", recycleBin.getRecycleid(), e);
            }
        }
        
        return count;
    }

    @Override
    public RecycleBinStatsVO getRecycleBinStats() {
        // 获取回收站项目总数
        long totalItems = count(new LambdaQueryWrapper<RecycleBin>()
                .eq(RecycleBin::getPermanentlyDeleted, false));
        
        // 获取即将过期的项目数量（7天内）
        LocalDateTime sevenDaysLater = LocalDateTime.now().plusDays(7);
        long expiringItems = count(new LambdaQueryWrapper<RecycleBin>()
                .eq(RecycleBin::getRecoveryStatus, false)
                .eq(RecycleBin::getPermanentlyDeleted, false)
                .le(RecycleBin::getPermanentDeleteTime, sevenDaysLater));
        
        // 获取已恢复项目数量
        long recoveredItems = count(new LambdaQueryWrapper<RecycleBin>()
                .eq(RecycleBin::getRecoveryStatus, true));
        
        // 获取已永久删除项目数量
        long permanentlyDeletedItems = count(new LambdaQueryWrapper<RecycleBin>()
                .eq(RecycleBin::getPermanentlyDeleted, true));
        
        // 构建统计数据
        return RecycleBinStatsVO.builder()
                .totalItems(totalItems)
                .expiringItems(expiringItems)
                .recoveredItems(recoveredItems)
                .permanentlyDeletedItems(permanentlyDeletedItems)
                .build();
    }
} 