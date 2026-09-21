/*
 回收站模块数据库结构
 创建日期: 2023-05-01
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 音乐资源表添加回收站相关字段 
-- ----------------------------
ALTER TABLE `music_resources`
ADD COLUMN `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否已删除：0-正常，1-已删除（在回收站）' AFTER `genre`,
ADD COLUMN `deleted_at` datetime(6) NULL DEFAULT NULL COMMENT '删除时间' AFTER `is_deleted`,
ADD COLUMN `deleted_by` bigint(20) NULL DEFAULT NULL COMMENT '删除人ID' AFTER `deleted_at`,
ADD COLUMN `retention_period` int(11) NULL DEFAULT 30 COMMENT '保留天数' AFTER `deleted_by`,
ADD COLUMN `permanent_delete_time` datetime(6) NULL DEFAULT NULL COMMENT '永久删除时间' AFTER `retention_period`,
ADD INDEX `idx_is_deleted`(`is_deleted`) USING BTREE,
ADD INDEX `idx_deleted_at`(`deleted_at`) USING BTREE,
ADD INDEX `idx_permanent_delete_time`(`permanent_delete_time`) USING BTREE;

-- ----------------------------
-- 回收站表
-- ----------------------------
DROP TABLE IF EXISTS `recycle_bin`;
CREATE TABLE `recycle_bin` (
  `recycleid` bigint(20) NOT NULL AUTO_INCREMENT,
  `deleted_at` datetime(6) NOT NULL,
  `recovery_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT '恢复状态：0-未恢复，1-已恢复',
  `permanently_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否永久删除：0-否，1-是',
  `permanent_delete_time` datetime(6) NULL DEFAULT NULL COMMENT '永久删除时间',
  `retention_period` int(11) NOT NULL DEFAULT 30 COMMENT '保留天数',
  `deleted_by` bigint(20) NOT NULL,
  `musicid` bigint(20) NOT NULL,
  `deleted_note` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '删除备注',
  PRIMARY KEY (`recycleid`) USING BTREE,
  INDEX `FKiwn68b5wwe1fybysj244ued7q`(`deleted_by` ASC) USING BTREE,
  INDEX `FK4ceopkja2jh3ar46nq8j0gaio`(`musicid` ASC) USING BTREE,
  INDEX `idx_recovery_status`(`recovery_status` ASC) USING BTREE,
  INDEX `idx_permanently_deleted`(`permanently_deleted` ASC) USING BTREE,
  INDEX `idx_permanent_delete_time`(`permanent_delete_time` ASC) USING BTREE,
  CONSTRAINT `FK4ceopkja2jh3ar46nq8j0gaio` FOREIGN KEY (`musicid`) REFERENCES `music_resources` (`musicid`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FKiwn68b5wwe1fybysj244ued7q` FOREIGN KEY (`deleted_by`) REFERENCES `users` (`userid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- 回收站设置表
-- ----------------------------
DROP TABLE IF EXISTS `recycle_bin_settings`;
CREATE TABLE `recycle_bin_settings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `default_retention_days` int(11) NOT NULL DEFAULT 30 COMMENT '默认保留天数',
  `auto_cleanup_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用自动清理：0-禁用，1-启用',
  `auto_cleanup_time` time NOT NULL DEFAULT '03:00:00' COMMENT '自动清理执行时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '回收站设置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- 初始化回收站设置
-- ----------------------------
INSERT INTO `recycle_bin_settings` (`id`, `default_retention_days`, `auto_cleanup_enabled`, `auto_cleanup_time`)
VALUES (1, 30, 1, '03:00:00');

SET FOREIGN_KEY_CHECKS = 1; 