package com.taffy.music.interceptor;

import com.taffy.music.annotation.Anonymous;
import com.taffy.music.utils.JwtUtil;
import com.taffy.music.utils.UserContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class JwtAuthenticationInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtil jwtUtil;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 检查是否有Anonymous注解
        if (hasAnonymousAnnotation(handler)) {
            // 匿名访问接口，允许通过但尝试提取token
            String token = extractToken(request);
            if (token != null && jwtUtil.validateToken(token)) {
                // 如果有有效token，仍然设置用户上下文
                setUserContext(token);
            }
            return true;
        }
        
        // 非匿名接口，必须验证token
        String token = extractToken(request);
        if (token == null) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }

        // 验证token
        if (!jwtUtil.validateToken(token)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }

        // 获取用户信息并存储在上下文中
        setUserContext(token);
        
        return true;
    }
    
    /**
     * 从请求中提取token
     */
    private String extractToken(HttpServletRequest request) {
        String token = request.getHeader("Authorization");
        if (token == null || !token.startsWith("Bearer ")) {
            return null;
        }
        return token.substring(7); // 去掉"Bearer "前缀
    }
    
    /**
     * 设置用户上下文
     */
    private void setUserContext(String token) {
        Long userId = jwtUtil.getUserIdFromToken(token);
        String email = jwtUtil.getEmailFromToken(token);
        UserContext.setContext(userId, email);
    }
    
    /**
     * 检查是否有Anonymous注解
     */
    private boolean hasAnonymousAnnotation(Object handler) {
        if (!(handler instanceof HandlerMethod)) {
            return false;
        }
        
        HandlerMethod handlerMethod = (HandlerMethod) handler;
        
        // 检查方法上是否有注解
        Anonymous methodAnnotation = handlerMethod.getMethod().getAnnotation(Anonymous.class);
        if (methodAnnotation != null) {
            return true;
        }
        
        // 检查类上是否有注解
        return handlerMethod.getBeanType().isAnnotationPresent(Anonymous.class);
    }
    
    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        // 请求完成后清理上下文
        UserContext.clear();
    }
}