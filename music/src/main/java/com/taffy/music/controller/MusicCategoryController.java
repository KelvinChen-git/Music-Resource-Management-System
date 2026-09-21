package com.taffy.music.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.domain.MusicCategory;
import com.taffy.music.service.MusicCategoryService;
import com.taffy.music.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/music-categories")
public class MusicCategoryController {

    @Autowired
    private MusicCategoryService categoryService;

    /**
     * 获取分类列表
     */
    @GetMapping
    public Result<Page<MusicCategory>> getCategories(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Page<MusicCategory> categories = categoryService.getCategories(current, size);
            return Result.success(categories);
        } catch (Exception e) {
            return Result.error("获取分类列表失败：" + e.getMessage());
        }
    }

    /**
     * 获取单个分类
     */
    @GetMapping("/{id}")
    public Result<MusicCategory> getCategory(@PathVariable("id") Integer categoryId) {
        try {
            MusicCategory category = categoryService.getById(categoryId);
            if (category == null) {
                return Result.error("分类不存在");
            }
            return Result.success(category);
        } catch (Exception e) {
            return Result.error("获取分类失败：" + e.getMessage());
        }
    }

    /**
     * 创建分类
     */
    @PostMapping
    public Result<MusicCategory> createCategory(@RequestBody MusicCategory category) {
        try {
            MusicCategory newCategory = categoryService.createCategory(category);
            return Result.success(newCategory);
        } catch (Exception e) {
            return Result.error("创建分类失败：" + e.getMessage());
        }
    }

    /**
     * 更新分类
     */
    @PutMapping("/{id}")
    public Result<MusicCategory> updateCategory(
            @PathVariable("id") Integer categoryId,
            @RequestBody MusicCategory category) {
        try {
            MusicCategory updatedCategory = categoryService.updateCategory(categoryId, category);
            return Result.success(updatedCategory);
        } catch (Exception e) {
            return Result.error("更新分类失败：" + e.getMessage());
        }
    }

    /**
     * 删除分类
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteCategory(@PathVariable("id") Integer categoryId) {
        try {
            categoryService.deleteCategory(categoryId);
            return Result.success();
        } catch (Exception e) {
            return Result.error("删除分类失败：" + e.getMessage());
        }
    }
} 