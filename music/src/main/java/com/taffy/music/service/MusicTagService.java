package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.MusicTags;

/**
 * 音乐标签服务接口
 */
public interface MusicTagService extends IService<MusicTags> {

    /**
     * 创建用户标签
     * @param userId 用户ID
     * @param tagName 标签名
     * @return 创建后的标签实体
     * @throws RuntimeException 如果标签名已存在（对于该用户）或校验失败
     */
    MusicTags createUserTag(Long userId, String tagName);

    /**
     * 分页获取指定用户的标签列表
     * @param userId 用户ID
     * @param page Mybatis-Plus分页对象
     * @return 包含标签数据的分页对象
     */
    Page<MusicTags> getTagsByUserId(Long userId, Page<MusicTags> page);

    /**
     * 获取用户拥有的特定标签
     * @param tagId 标签ID
     * @param userId 用户ID
     * @return 标签实体
     * @throws RuntimeException 如果标签不存在或不属于该用户
     */
    MusicTags getUserTagById(Long tagId, Long userId);

    /**
     * 更新用户拥有的标签名称
     * @param tagId 标签ID
     * @param userId 用户ID
     * @param newTagName 新的标签名
     * @return 更新后的标签实体
     * @throws RuntimeException 如果标签不存在、不属于该用户，或新名称已存在（对于该用户）
     * @throws IllegalArgumentException 如果新名称校验失败
     */
    MusicTags updateUserTag(Long tagId, Long userId, String newTagName);

    /**
     * 删除用户拥有的特定标签
     * @param tagId 标签ID
     * @param userId 用户ID
     * @throws RuntimeException 如果标签不存在或不属于该用户
     */
    void deleteUserTag(Long tagId, Long userId);
} 