package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.MusicCategory;

public interface MusicCategoryService extends IService<MusicCategory> {
    
    /**
     * 分页获取分类列表
     */
    Page<MusicCategory> getCategories(int current, int size);
    
    /**
     * 根据名称查找分类
     */
    MusicCategory getCategoryByName(String categoryName);
    
    /**
     * 创建新分类
     */
    MusicCategory createCategory(MusicCategory category);
    
    /**
     * 更新分类
     */
    MusicCategory updateCategory(Integer categoryId, MusicCategory category);
    
    /**
     * 删除分类
     */
    void deleteCategory(Integer categoryId);
} 