package com.taffy.music.utils;

import lombok.Data;

/**
 * 用户上下文信息
 */
@Data
public class UserContext {
    
    /**
     * 用户ID
     */
    private Long userId;
    
    /**
     * 用户邮箱
     */
    private String email;
    
    /**
     * 线程本地变量，存储用户上下文信息
     */
    private static final ThreadLocal<UserContext> userContextThreadLocal = new ThreadLocal<>();
    
    /**
     * 获取当前用户上下文
     */
    public static UserContext getCurrentContext() {
        UserContext context = userContextThreadLocal.get();
        if (context == null) {
            context = new UserContext();
            userContextThreadLocal.set(context);
        }
        return context;
    }
    
    /**
     * 设置用户上下文
     */
    public static void setContext(Long userId, String email) {
        UserContext context = getCurrentContext();
        context.setUserId(userId);
        context.setEmail(email);
    }
    
    /**
     * 获取当前用户ID
     */
    public static Long getCurrentUserId() {
        return getCurrentContext().getUserId();
    }
    
    /**
     * 获取当前用户邮箱
     */
    public static String getCurrentUserEmail() {
        return getCurrentContext().getEmail();
    }
    
    /**
     * 清除用户上下文
     */
    public static void clear() {
        userContextThreadLocal.remove();
    }

} 