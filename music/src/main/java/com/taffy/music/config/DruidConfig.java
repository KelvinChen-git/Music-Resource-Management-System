package com.taffy.music.config;

import com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceBuilder;
import com.alibaba.druid.spring.boot.autoconfigure.properties.DruidStatProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;

@Configuration
public class DruidConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.druid")
    public DataSource dataSource() {
        return DruidDataSourceBuilder.create().build();
    }

    /**
     * Druid监控配置
     * 注：在Spring Boot 3.x中，我们使用application.properties/yml配置方式替代FilterRegistrationBean
     * 例如：
     * spring.datasource.druid.web-stat-filter.enabled=true
     * spring.datasource.druid.web-stat-filter.url-pattern=/*
     * spring.datasource.druid.web-stat-filter.exclusions=*.js,*.gif,*.jpg,*.png,*.css,*.ico,/druid/*
     * spring.datasource.druid.stat-view-servlet.enabled=true
     * spring.datasource.druid.stat-view-servlet.url-pattern=/druid/*
     * spring.datasource.druid.stat-view-servlet.login-username=admin
     * spring.datasource.druid.stat-view-servlet.login-password=admin
     */
} 