package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.MusicTags;
import com.taffy.music.mapper.MusicTagMapper;
import com.taffy.music.service.MusicTagService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 音乐标签服务实现类
 */
@Slf4j
@Service
public class MusicTagServiceImpl extends ServiceImpl<MusicTagMapper, MusicTags> implements MusicTagService {

    @Override
    @Transactional
    public MusicTags createUserTag(Long userId, String tagName) {
        // 输入校验
        if (!StringUtils.hasText(tagName)) {
            throw new IllegalArgumentException("Tag name cannot be empty");
        }
        if (tagName.length() > 50) {
            throw new IllegalArgumentException("Tag name cannot exceed 50 characters");
        }

        // 唯一性校验 (用户范围内，不区分大小写)
        LambdaQueryWrapper<MusicTags> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MusicTags::getUserId, userId)
               .apply("LOWER(tag_name) = LOWER({0})", tagName);
        long count = this.count(wrapper);
        if (count > 0) {
            throw new RuntimeException("Tag with this name already exists for the user.");
        }

        // 创建并保存
        MusicTags newTag = new MusicTags();
        newTag.setUserId(userId);
        newTag.setTagName(tagName); // 保存原始大小写
        this.save(newTag);
        return newTag;
    }

    @Override
    public Page<MusicTags> getTagsByUserId(Long userId, Page<MusicTags> page) {
        LambdaQueryWrapper<MusicTags> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MusicTags::getUserId, userId);
        wrapper.orderByAsc(MusicTags::getTagName); // Default sort by tag name
        return this.page(page, wrapper);
    }

    @Override
    public MusicTags getUserTagById(Long tagId, Long userId) {
        LambdaQueryWrapper<MusicTags> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MusicTags::getTagId, tagId)
               .eq(MusicTags::getUserId, userId);
        MusicTags tag = this.getOne(wrapper);
        if (tag == null) {
            throw new RuntimeException("Tag not found or does not belong to the user.");
        }
        return tag;
    }

    @Override
    @Transactional
    public MusicTags updateUserTag(Long tagId, Long userId, String newTagName) {
        // 校验新名称
        if (!StringUtils.hasText(newTagName)) {
            throw new IllegalArgumentException("Tag name cannot be empty");
        }
        if (newTagName.length() > 50) {
            throw new IllegalArgumentException("Tag name cannot exceed 50 characters");
        }

        // 检查所有权并获取旧标签
        MusicTags existingTag = this.getUserTagById(tagId, userId); // This checks ownership

        // 如果新名称与旧名称相同（忽略大小写），则无需更新
        if (newTagName.equalsIgnoreCase(existingTag.getTagName())) {
            return existingTag;
        }

        // 检查新名称唯一性 (排除自身)
        LambdaQueryWrapper<MusicTags> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MusicTags::getUserId, userId)
               .ne(MusicTags::getTagId, tagId)
               .apply("LOWER(tag_name) = LOWER({0})", newTagName);
        long count = this.count(wrapper);
        if (count > 0) {
            throw new RuntimeException("Another tag with this name already exists for the user.");
        }

        // 更新标签
        existingTag.setTagName(newTagName);
        this.updateById(existingTag);

        return existingTag;
    }

    @Override
    @Transactional
    public void deleteUserTag(Long tagId, Long userId) {
        // 检查所有权
        this.getUserTagById(tagId, userId); // This checks ownership

        // 删除标签
        boolean removed = this.removeById(tagId);
        if (!removed) {
            log.warn("Tag with id {} claimed to exist but removeById returned false.", tagId);
        }
    }
}