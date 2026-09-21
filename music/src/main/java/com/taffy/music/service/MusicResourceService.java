package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.vo.MusicMetadataVO;

import java.util.List;

/**
 * 音乐资源服务接口
 */
public interface MusicResourceService extends IService<MusicResources> {
    /**
     * 获取音乐资源列表
     * @param title 标题
     * @param artist 艺术家
     * @param album 专辑
     * @param categoryId 分类ID
     * @param onlyMine 是否只显示当前用户的音乐
     * @param current 当前页
     * @param pageSize 每页大小
     * @param tagIds 标签ID列表
     * @param keyword 模糊搜索关键词 (匹配 additional_metadata, album, approval_status, artist, genre)
     * @return 分页结果
     */
    Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, Boolean onlyMine, Integer current, Integer pageSize, List<Long> tagIds, String keyword);
    
    /**
     * 获取音乐资源列表（支持按用户名和邮箱过滤）
     * @param title 标题
     * @param artist 艺术家
     * @param album 专辑
     * @param categoryId 分类ID
     * @param onlyMine 是否只显示当前用户的音乐
     * @param current 当前页
     * @param pageSize 每页大小
     * @param userIdByName 通过用户名查找的用户ID
     * @param userIdByEmail 通过邮箱查找的用户ID
     * @param tagIds 标签ID列表
     * @param keyword 模糊搜索关键词
     * @return 分页结果
     */
    Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, List<Long> tagIds, String keyword);

    /**
     * 获取音乐资源列表（支持按用户名、邮箱和审核状态过滤）
     * @param title 标题
     * @param artist 艺术家
     * @param album 专辑
     * @param categoryId 分类ID
     * @param onlyMine 是否只显示当前用户的音乐
     * @param current 当前页
     * @param pageSize 每页大小
     * @param userIdByName 通过用户名查找的用户ID
     * @param userIdByEmail 通过邮箱查找的用户ID
     * @param approvalStatus 审核状态
     * @param tagIds 标签ID列表
     * @param keyword 模糊搜索关键词
     * @return 分页结果
     */
    Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, String approvalStatus, List<Long> tagIds, String keyword);

    /**
     * 根据ID获取音乐资源
     * @param id 音乐资源ID
     * @return 音乐资源
     */
    MusicResources getMusicResourceById(Integer id);

    /**
     * 更新音乐资源
     * @param id 音乐资源ID
     * @param metadata 元数据 (包含tagIds)
     * @return 是否成功
     */
    boolean updateMusicResource(Long id, MusicMetadataVO metadata);

    /**
     * 解析并保存音乐元数据
     * @param fileId 文件ID
     * @param metadata 元数据
     * @return 解析后的元数据
     */
    MusicMetadataVO parseAndSaveMetadata(Long fileId, MusicMetadataVO metadata);

    /**
     * 审核音乐资源
     * @param id 音乐资源ID
     * @return 是否成功
     */
    boolean approveMusicResource(Integer id);
    
    /**
     * 拒绝音乐资源审核
     * @param id 音乐资源ID
     * @return 是否成功
     */
    boolean rejectMusicResource(Integer id);
    
    /**
     * 将音乐资源移动到回收站
     * @param id 音乐资源ID
     * @param deleteNote 删除备注
     * @return 是否成功
     */
    boolean moveToRecycleBin(Long id, String deleteNote);
    
    /**
     * 从回收站恢复音乐资源
     * @param id 音乐资源ID
     * @return 是否成功
     */
    boolean restoreFromRecycleBin(Long id);
    
    /**
     * 获取音乐资源列表(包括回收站选项)
     * @param title 标题
     * @param artist 艺术家
     * @param album 专辑
     * @param categoryId 分类ID
     * @param onlyMine 是否只显示当前用户的音乐
     * @param includeDeleted 是否包括已删除的音乐
     * @param current 当前页
     * @param pageSize 每页大小
     * @param tagIds 标签ID列表
     * @param keyword 模糊搜索关键词
     * @return 分页结果
     */
    Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, 
        Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize, List<Long> tagIds, String keyword);
    
    /**
     * 获取音乐资源列表(包括回收站选项，支持按用户名和邮箱过滤)
     * @param title 标题
     * @param artist 艺术家
     * @param album 专辑
     * @param categoryId 分类ID
     * @param onlyMine 是否只显示当前用户的音乐
     * @param includeDeleted 是否包括已删除的音乐
     * @param current 当前页
     * @param pageSize 每页大小
     * @param userIdByName 通过用户名查找的用户ID
     * @param userIdByEmail 通过邮箱查找的用户ID
     * @param tagIds 标签ID列表
     * @param keyword 模糊搜索关键词
     * @return 分页结果
     */
    Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, 
        Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize,
        Long userIdByName, Long userIdByEmail, List<Long> tagIds, String keyword);

    Page<MusicResources> getMusicResourceList(String title, String artist, String album, Integer categoryId, 
                                             Boolean onlyMine, Integer current, Integer pageSize, 
                                             Long userIdByName, Long userIdByEmail, String approvalStatus, 
                                             String orderBy, String orderType, List<Long> tagIds,
                                             String startDate, String endDate, String keyword);
                                             
    Page<MusicResources> getMusicResourceListWithDeletedOption(String title, String artist, String album, 
        Integer categoryId, Boolean onlyMine, Boolean includeDeleted, Integer current, Integer pageSize, 
        Long userIdByName, Long userIdByEmail, String orderBy, String orderType, List<Long> tagIds,
        String keyword);

    void incrementPlayCount(Long musicId);

    /**
     * 更新指定音乐资源的标签关联
     * @param musicId 音乐资源ID
     * @param userId 当前用户ID (用于校验标签所有权)
     * @param tagIds 要关联的标签ID列表 (来自用户选择)
     */
    void updateMusicTags(Long musicId, Long userId, List<Long> tagIds);

    /**
     * 删除音乐资源，如果物理文件不存在则直接删除记录，否则移入回收站。
     * @param musicId 音乐资源ID
     * @param deleteNote 删除备注 (用于回收站)
     * @return 操作是否成功 (true 表示成功删除或移入回收站)
     * @throws RuntimeException 如果资源不存在或发生其他错误
     */
    boolean deleteMusicResourceConditionally(Long musicId, String deleteNote);
} 