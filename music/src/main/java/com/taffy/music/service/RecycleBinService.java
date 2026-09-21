package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.vo.RecycleBinStatsVO;

import java.util.List;

/**
 * 回收站服务接口
 */
public interface RecycleBinService extends IService<RecycleBin> {
    
    /**
     * 获取回收站音乐列表
     * @param title 标题
     * @param artist 艺术家
     * @param current 当前页
     * @param pageSize 每页大小
     * @return 分页结果
     */
    @Deprecated
    Page<RecycleBin> getRecycleBinList(String title, String artist, Integer current, Integer pageSize);
    
    /**
     * 获取回收站音乐列表（支持按用户ID过滤）
     * @param title 标题
     * @param artist 艺术家
     * @param current 当前页
     * @param pageSize 每页大小
     * @param userId 用户ID（为null时不过滤）
     * @return 分页结果
     */
    Page<RecycleBin> getRecycleBinList(String title, String artist, Integer current, Integer pageSize, Long userId);
    
    /**
     * 将音乐资源移动到回收站
     * @param musicId 音乐资源ID
     * @param deleteNote 删除备注
     * @return 是否成功
     */
    boolean moveToRecycleBin(Long musicId, String deleteNote);
    
    /**
     * 从回收站恢复音乐资源
     * @param recycleBinId 回收站记录ID
     * @return 恢复后的音乐资源
     */
    MusicResources restoreFromRecycleBin(Long recycleBinId);
    
    /**
     * 从回收站中永久删除音乐资源
     * @param recycleBinId 回收站记录ID
     * @return 是否成功
     */
    boolean deleteFromRecycleBin(Long recycleBinId);
    
    /**
     * 清空回收站 (批量永久删除)
     * @return 删除的记录数
     */
    int emptyRecycleBin();
    
    /**
     * 获取即将过期的回收站项目
     * @param days 天数
     * @return 即将过期的项目列表
     */
    List<RecycleBin> getExpiredItems(int days);
    
    /**
     * 自动清理过期的回收站项目
     * @return 清理的数量
     */
    int autoCleanupExpiredItems();
    
    /**
     * 获取回收站统计数据
     * @return 统计数据
     */
    RecycleBinStatsVO getRecycleBinStats();

    /**
     * 清空指定用户的回收站项目
     * @param userId 要清空回收站的用户ID
     * @return 成功删除的项目数量
     */
    int emptyUserRecycleBin(Long userId);
} 