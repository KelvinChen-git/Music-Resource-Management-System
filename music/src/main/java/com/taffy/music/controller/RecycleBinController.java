package com.taffy.music.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.common.Result;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.service.RecycleBinService;
import com.taffy.music.service.UserService;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.UserVO;
import com.taffy.music.vo.RecycleBinStatsVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 回收站控制器
 */
@Slf4j
@RestController
@RequestMapping("/recycle-bin")
public class RecycleBinController {

    @Autowired
    private RecycleBinService recycleBinService;

    @Autowired
    private UserService userService;

    /**
     * 获取回收站列表
     */
    @GetMapping("/list")
    public Result<Page<RecycleBin>> list(
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String artist,
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        try {
            // 验证用户权限
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 获取当前用户信息，检查角色
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());
            
            // 如果不是管理员，只能查看自己的回收站内容
            Long userIdFilter = isAdmin ? null : currentUserId;

            // 获取带音乐和用户信息的回收站列表，传入用户ID过滤条件
            Page<RecycleBin> page = recycleBinService.getRecycleBinList(title, artist, current, pageSize, userIdFilter);
            
            // 过滤掉实际在 service 中未能通过条件过滤的记录
            // 注意：这种方式会影响实际分页结果，理想情况下应该在查询时就过滤
            // 但由于我们基于关联对象进行过滤，需要在获取后再进行过滤操作
            if (page.getRecords() != null && !page.getRecords().isEmpty()) {
                page.getRecords().removeIf(recycleBin -> 
                    (recycleBin.getMusic() == null) ||
                    (title != null && !title.isEmpty() && !recycleBin.getMusic().getTitle().contains(title)) ||
                    (artist != null && !artist.isEmpty() && !recycleBin.getMusic().getArtist().contains(artist))
                );
            }
            
            return Result.success(page);
        } catch (Exception e) {
            log.error("获取回收站列表失败", e);
            return Result.error("获取回收站列表失败：" + e.getMessage());
        }
    }

    /**
     * 从回收站恢复音乐资源
     */
    @PostMapping("/{id}/restore")
    public Result<MusicResources> restore(@PathVariable Long id) {
        try {
            // 验证用户权限
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 获取当前用户信息，检查角色
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());
            
            // 验证是否有权限恢复此项目
            RecycleBin recycleBin = recycleBinService.getById(id);
            if (recycleBin == null) {
                return Result.error("回收站项目不存在");
            }
            
            // 非管理员只能恢复自己的文件
            if (!isAdmin && !currentUserId.equals(recycleBin.getDeletedById())) {
                return Result.error("您没有权限恢复此项目");
            }

            // 执行恢复操作
            MusicResources music = recycleBinService.restoreFromRecycleBin(id);
            return Result.success(music);
        } catch (Exception e) {
            log.error("恢复音乐资源失败", e);
            return Result.error("恢复音乐资源失败：" + e.getMessage());
        }
    }

    /**
     * 从回收站永久删除音乐资源
     */
    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        try {
            // 验证用户权限
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 获取当前用户信息，检查角色
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());

            // 获取要删除的回收站记录
            RecycleBin recycleBin = recycleBinService.getById(id);
            if (recycleBin == null) {
                return Result.error(404, "Recycle bin item not found");
            }

            // 权限检查：管理员或项目删除者可以删除
            if (!isAdmin && (recycleBin.getDeletedById() == null || !recycleBin.getDeletedById().equals(currentUserId))) {
                 return Result.error(403, "You do not have permission to delete this item.");
            }

            // 执行永久删除操作
            boolean success = recycleBinService.deleteFromRecycleBin(id);
            return success ? Result.success(true) : Result.error("Failed to permanently delete the item");
        } catch (Exception e) {
            log.error("永久删除音乐资源失败", e);
            return Result.error("Failed to permanently delete the item: " + e.getMessage());
        }
    }

    /**
     * 清空回收站
     */
    @DeleteMapping("/empty")
    public Result<Integer> emptyRecycleBin() {
        try {
            // 验证用户权限
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 获取当前用户信息，检查角色
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());

            // 如果用户不是管理员，拒绝操作
            if (!isAdmin) {
                return Result.error("只有管理员可以清空回收站");
            }

            // 执行清空回收站操作
            int count = recycleBinService.emptyRecycleBin();
            return Result.success(count);
        } catch (Exception e) {
            log.error("清空回收站失败", e);
            return Result.error("清空回收站失败：" + e.getMessage());
        }
    }

    /**
     * 清空当前用户自己的回收站项目
     */
    @DeleteMapping("/empty-mine")
    public Result<Integer> emptyMyRecycleBin() {
        try {
            // 获取当前用户ID
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 调用服务层方法清空当前用户的回收站项目
            int count = recycleBinService.emptyUserRecycleBin(currentUserId);
            return Result.success(count);
        } catch (Exception e) {
            log.error("清空用户回收站失败, userId: {}", UserContext.getCurrentUserId(), e);
            return Result.error("Failed to empty your recycle bin items: " + e.getMessage());
        }
    }

    /**
     * 获取回收站统计数据
     */
    @GetMapping("/stats")
    public Result<RecycleBinStatsVO> getRecycleBinStats() {
        try {
            // 验证用户权限
            Long currentUserId = UserContext.getCurrentUserId();
            if (currentUserId == null) {
                return Result.error("请先登录");
            }

            // 获取当前用户信息，检查角色
            UserVO currentUser = userService.getCurrentUserInfo();
            boolean isAdmin = "ADMIN".equals(currentUser.getRole());

            // 如果用户不是管理员，拒绝操作
            if (!isAdmin) {
                return Result.error("只有管理员可以查看回收站统计数据");
            }

            // 获取回收站统计数据
            RecycleBinStatsVO stats = recycleBinService.getRecycleBinStats();
            return Result.success(stats);
        } catch (Exception e) {
            log.error("获取回收站统计数据失败", e);
            return Result.error("获取回收站统计数据失败：" + e.getMessage());
        }
    }
} 