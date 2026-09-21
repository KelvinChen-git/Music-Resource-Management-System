-- 用户表：存储系统用户信息
CREATE TABLE `users` (
    `user_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID，主键',
    `name` VARCHAR(50) NOT NULL COMMENT '用户名称',
    `email` VARCHAR(100) NOT NULL UNIQUE COMMENT '用户邮箱，唯一',
    `avatar` VARCHAR(255) COMMENT '用户头像URL',
    `password` VARCHAR(255) NOT NULL COMMENT '用户密码（加密存储）',
    `role` VARCHAR(20) NOT NULL DEFAULT 'User' COMMENT '用户角色，如：Admin、User',
    `verification_status` BOOLEAN DEFAULT FALSE COMMENT '验证状态：true-已验证，false-未验证',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';

-- 音乐分类表：存储音乐分类信息
CREATE TABLE `music_categories` (
    `category_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '分类ID，主键',
    `category_name` VARCHAR(50) NOT NULL UNIQUE COMMENT '分类名称，唯一',
    `description` VARCHAR(255) COMMENT '分类描述',
    INDEX `idx_category_name` (`category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='音乐分类表';

-- 音乐资源表：存储音乐文件信息
CREATE TABLE `music_resources` (
    `musicid` BIGINT NOT NULL AUTO_INCREMENT,
    `additional_metadata` TEXT,
    `album` VARCHAR(255) DEFAULT NULL,
    `approval_status` VARCHAR(255) DEFAULT NULL,
    `artist` VARCHAR(255) DEFAULT NULL,
    `file_path` VARCHAR(255) DEFAULT NULL,
    `file_size` INT DEFAULT NULL,
    `format` VARCHAR(255) DEFAULT NULL,
    `title` VARCHAR(255) DEFAULT NULL,
    `upload_time` DATETIME(6) DEFAULT NULL,
    `categoryid` BIGINT NOT NULL,
    `userid` BIGINT NOT NULL,
    `genre` VARCHAR(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '音乐流派',
    PRIMARY KEY (`musicid`),
    KEY `FK7yx2yacxhljih6yj9fy62vhr5` (`categoryid`),
    KEY `FK2m4su9xuj1c0245wjdda659eq` (`userid`),
    CONSTRAINT `FK2m4su9xuj1c0245wjdda659eq` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`),
    CONSTRAINT `FK7yx2yacxhljih6yj9fy62vhr5` FOREIGN KEY (`categoryid`) REFERENCES `music_categories` (`categoryid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 音乐标签表：存储系统和用户自定义标签
CREATE TABLE `music_tags` (
    `tag_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '标签ID，主键',
    `user_id` INT COMMENT '创建用户ID，NULL表示系统标签',
    `tag_name` VARCHAR(50) NOT NULL COMMENT '标签名称',
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
    UNIQUE KEY `uk_user_tag` (`user_id`, `tag_name`),
    INDEX `idx_tag_name` (`tag_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='音乐标签表';

-- 音乐资源标签关联表：存储音乐与标签的多对多关系
CREATE TABLE `music_resource_tags` (
    `music_id` INT NOT NULL COMMENT '音乐ID',
    `tag_id` INT NOT NULL COMMENT '标签ID',
    PRIMARY KEY (`music_id`, `tag_id`),
    FOREIGN KEY (`music_id`) REFERENCES `music_resources` (`musicid`),
    FOREIGN KEY (`tag_id`) REFERENCES `music_tags` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='音乐-标签关联表';

-- 审计日志表：记录音乐资源的审核操作日志
CREATE TABLE `audit_logs` (
    `audit_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '审计ID，主键',
    `music_id` INT NOT NULL COMMENT '音乐ID',
    `admin_id` INT NOT NULL COMMENT '审核管理员ID',
    `action` VARCHAR(50) NOT NULL COMMENT '审核动作：Approved-通过，Rejected-拒绝',
    `reason` VARCHAR(255) COMMENT '审核原因',
    `audit_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审核时间',
    FOREIGN KEY (`music_id`) REFERENCES `music_resources` (`musicid`),
    FOREIGN KEY (`admin_id`) REFERENCES `users` (`user_id`),
    INDEX `idx_audit_time` (`audit_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';

-- 回收站表：存储被删除的音乐资源
CREATE TABLE `recycle_bin` (
    `recycle_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '回收ID，主键',
    `music_id` INT NOT NULL COMMENT '音乐ID',
    `deleted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '删除时间',
    `deleted_by` INT NOT NULL COMMENT '执行删除的用户ID',
    `deleted_data` JSON NOT NULL COMMENT '删除时的资源数据快照，JSON格式',
    `permanent_deletion_time` DATETIME COMMENT '永久删除时间，NULL表示可恢复',
    FOREIGN KEY (`music_id`) REFERENCES `music_resources` (`musicid`),
    FOREIGN KEY (`deleted_by`) REFERENCES `users`
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回收站表';