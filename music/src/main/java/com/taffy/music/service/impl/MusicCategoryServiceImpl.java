package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.MusicCategory;
import com.taffy.music.mapper.MusicCategoryMapper;
import com.taffy.music.service.MusicCategoryService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MusicCategoryServiceImpl extends ServiceImpl<MusicCategoryMapper, MusicCategory> implements MusicCategoryService {

    @Override
    public Page<MusicCategory> getCategories(int current, int size) {
        Page<MusicCategory> page = new Page<>(current, size);
        return page(page);
    }

    @Override
    public MusicCategory getCategoryByName(String categoryName) {
        LambdaQueryWrapper<MusicCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MusicCategory::getCategoryName, categoryName);
        return getOne(wrapper);
    }

    @Override
    @Transactional
    public MusicCategory createCategory(MusicCategory category) {
        // 检查分类名称是否已存在
        MusicCategory existingCategory = getCategoryByName(category.getCategoryName());
        if (existingCategory != null) {
            throw new RuntimeException("分类名称已存在");
        }
        
        save(category);
        return category;
    }

    @Override
    @Transactional
    public MusicCategory updateCategory(Integer categoryId, MusicCategory category) {
        // 检查分类是否存在
        MusicCategory existingCategory = getById(categoryId);
        if (existingCategory == null) {
            throw new RuntimeException("分类不存在");
        }
        
        // 如果更新了分类名称，检查新名称是否与其他分类重复
        if (!existingCategory.getCategoryName().equals(category.getCategoryName())) {
            MusicCategory categoryWithSameName = getCategoryByName(category.getCategoryName());
            if (categoryWithSameName != null) {
                throw new RuntimeException("分类名称已存在");
            }
        }
        
        category.setCategoryId(categoryId);
        updateById(category);
        return category;
    }

    @Override
    @Transactional
    public void deleteCategory(Integer categoryId) {
        // 检查分类是否存在
        MusicCategory category = getById(categoryId);
        if (category == null) {
            throw new RuntimeException("分类不存在");
        }
        
        removeById(categoryId);
    }
} 