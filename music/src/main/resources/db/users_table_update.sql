-- 为users表添加锁定相关字段和更新字段注释
ALTER TABLE `users`
ADD COLUMN `is_locked` bit(1) NOT NULL DEFAULT b'0' COMMENT '账户是否被锁定：0-未锁定，1-已锁定',
ADD COLUMN `lock_reason` varchar(255) DEFAULT NULL COMMENT '账户锁定原因',
ADD COLUMN `lock_time` datetime(6) DEFAULT NULL COMMENT '账户锁定时间',
ADD COLUMN `unlock_time` datetime(6) DEFAULT NULL COMMENT '账户解锁时间',
MODIFY COLUMN `verification_status` bit(1) DEFAULT b'0' COMMENT '账户验证状态：0-未验证，1-已验证';

-- 添加索引以提高查询效率
CREATE INDEX `idx_user_locked` ON `users` (`is_locked`); 