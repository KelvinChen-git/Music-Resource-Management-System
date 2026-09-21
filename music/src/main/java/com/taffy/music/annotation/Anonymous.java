package com.taffy.music.annotation;

import java.lang.annotation.*;

/**
 * 匿名访问注解
 * 
 * 标记了此注解的接口可以匿名访问，无需进行Token认证
 * 如果接口中带有有效Token，将会正常解析并设置用户上下文
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Anonymous {
} 