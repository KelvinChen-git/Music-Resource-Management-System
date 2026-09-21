package com.taffy.music.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.common.Result;
import com.taffy.music.domain.MusicTags;
import com.taffy.music.dto.TagCreateDTO;
import com.taffy.music.dto.TagUpdateDTO;
import com.taffy.music.service.MusicTagService;
import com.taffy.music.utils.UserContext;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/tags")
@Slf4j
public class MusicTagController {

    @Autowired
    private MusicTagService musicTagService;

    @PostMapping
    public Result<MusicTags> createTag(@Valid @RequestBody TagCreateDTO tagCreateDTO) {
        try {
            Long userId = UserContext.getCurrentUserId();
            if (userId == null) {
                return Result.error(401, "User not logged in");
            }
            MusicTags createdTag = musicTagService.createUserTag(userId, tagCreateDTO.getTagName());
            return Result.success(createdTag);
        } catch (RuntimeException e) {
            log.warn("Failed to create tag: {}", e.getMessage());
            return Result.error(e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error creating tag", e);
            return Result.error("Failed to create tag");
        }
    }

    @GetMapping
    public Result<Page<MusicTags>> getTags(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Long userId = UserContext.getCurrentUserId();
            if (userId == null) {
                return Result.error(401, "User not logged in");
            }
            Page<MusicTags> page = new Page<>(current, size);
            Page<MusicTags> resultPage = musicTagService.getTagsByUserId(userId, page);
            return Result.success(resultPage);
        } catch (Exception e) {
            log.error("Failed to get tags for user", e);
            return Result.error("Failed to retrieve tags");
        }
    }

    @GetMapping("/{id}")
    public Result<MusicTags> getTagById(@PathVariable Long id) {
        try {
            Long userId = UserContext.getCurrentUserId();
            if (userId == null) {
                return Result.error(401, "User not logged in");
            }
            MusicTags tag = musicTagService.getUserTagById(id, userId);
            return Result.success(tag);
        } catch (RuntimeException e) {
            log.warn("Failed to get tag by id {} for user: {}", id, e.getMessage());
            return Result.error(e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error getting tag by id {}", id, e);
            return Result.error("Failed to retrieve tag");
        }
    }

    @PutMapping("/{id}")
    public Result<MusicTags> updateTag(@PathVariable Long id, @Valid @RequestBody TagUpdateDTO tagUpdateDTO) {
        try {
            Long userId = UserContext.getCurrentUserId();
            if (userId == null) {
                return Result.error(401, "User not logged in");
            }
            MusicTags updatedTag = musicTagService.updateUserTag(id, userId, tagUpdateDTO.getTagName());
            return Result.success(updatedTag);
        } catch (RuntimeException e) {
            log.warn("Failed to update tag id {}: {}", id, e.getMessage());
            return Result.error(e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error updating tag id {}", id, e);
            return Result.error("Failed to update tag");
        }
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteTag(@PathVariable Long id) {
        try {
            Long userId = UserContext.getCurrentUserId();
            if (userId == null) {
                return Result.error(401, "User not logged in");
            }
            musicTagService.deleteUserTag(id, userId);
            return Result.success();
        } catch (RuntimeException e) {
            log.warn("Failed to delete tag id {}: {}", id, e.getMessage());
            return Result.error(e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error deleting tag id {}", id, e);
            return Result.error("Failed to delete tag");
        }
    }
}