/*
 Navicat Premium Dump SQL

 Source Server         : 本地洗衣机
 Source Server Type    : MySQL
 Source Server Version : 80012 (8.0.12)
 Source Host           : localhost:3306
 Source Schema         : music_db

 Target Server Type    : MySQL
 Target Server Version : 80012 (8.0.12)
 File Encoding         : 65001

 Date: 08/04/2025 23:19:05
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for audit_logs
-- ----------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs`  (
  `auditid` bigint(20) NOT NULL AUTO_INCREMENT,
  `action` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `audit_time` datetime(6) NULL DEFAULT NULL,
  `reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `adminid` bigint(20) NOT NULL,
  `musicid` bigint(20) NOT NULL,
  PRIMARY KEY (`auditid`) USING BTREE,
  INDEX `FKjhofa8q4o1lwa30sigmujfxey`(`adminid` ASC) USING BTREE,
  INDEX `FKoctdjal2qy489wpd73wie2a8e`(`musicid` ASC) USING BTREE,
  CONSTRAINT `FKjhofa8q4o1lwa30sigmujfxey` FOREIGN KEY (`adminid`) REFERENCES `users` (`userid`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FKoctdjal2qy489wpd73wie2a8e` FOREIGN KEY (`musicid`) REFERENCES `music_resources` (`musicid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for file_chunk
-- ----------------------------
DROP TABLE IF EXISTS `file_chunk`;
CREATE TABLE `file_chunk`  (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_id` bigint(20) NOT NULL COMMENT '文件ID',
  `chunk_index` int(11) NOT NULL COMMENT '分片索引',
  `chunk_size` int(11) NOT NULL COMMENT '分片大小(字节)',
  `chunk_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '分片存储路径',
  `chunk_md5` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '分片MD5值',
  `status` tinyint(4) NOT NULL DEFAULT 0 COMMENT '状态：0-未上传，1-已上传',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否删除',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_file_chunk`(`file_id` ASC, `chunk_index` ASC) USING BTREE,
  INDEX `idx_file_id`(`file_id` ASC) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  CONSTRAINT `file_chunk_ibfk_1` FOREIGN KEY (`file_id`) REFERENCES `file_upload` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 54 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '文件分片表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for file_upload
-- ----------------------------
DROP TABLE IF EXISTS `file_upload`;
CREATE TABLE `file_upload`  (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件名',
  `file_size` bigint(20) NOT NULL COMMENT '文件大小(字节)',
  `file_md5` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件MD5值',
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件存储路径',
  `file_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件类型',
  `chunk_size` int(11) NOT NULL COMMENT '分片大小(字节)',
  `chunk_count` int(11) NOT NULL COMMENT '总分片数',
  `uploaded_chunks` int(11) NOT NULL DEFAULT 0 COMMENT '已上传分片数',
  `status` tinyint(4) NOT NULL DEFAULT 0 COMMENT '状态：0-上传中，1-上传完成，2-上传失败',
  `upload_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `complete_time` datetime NULL DEFAULT NULL COMMENT '完成时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否删除',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  INDEX `idx_create_time`(`create_time` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '文件上传表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for music_categories
-- ----------------------------
DROP TABLE IF EXISTS `music_categories`;
CREATE TABLE `music_categories`  (
  `categoryid` bigint(20) NOT NULL AUTO_INCREMENT,
  `category_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`categoryid`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for music_resource_tags
-- ----------------------------
DROP TABLE IF EXISTS `music_resource_tags`;
CREATE TABLE `music_resource_tags`  (
  `musicid` bigint(20) NOT NULL,
  `tagid` bigint(20) NOT NULL,
  PRIMARY KEY (`musicid`, `tagid`) USING BTREE,
  INDEX `FKeqx92ykm06205hvry16blvph2`(`tagid` ASC) USING BTREE,
  CONSTRAINT `FKa4sqjffeimbu8bja06pxqhtsh` FOREIGN KEY (`musicid`) REFERENCES `music_resources` (`musicid`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FKeqx92ykm06205hvry16blvph2` FOREIGN KEY (`tagid`) REFERENCES `music_tags` (`tagid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for music_resources
-- ----------------------------
DROP TABLE IF EXISTS `music_resources`;
CREATE TABLE `music_resources`  (
  `musicid` bigint(20) NOT NULL AUTO_INCREMENT,
  `additional_metadata` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `album` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `approval_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '审核状态: pending, approved, rejected',
  `artist` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `file_size` int(11) NULL DEFAULT NULL,
  `format` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `upload_time` datetime(6) NULL DEFAULT NULL,
  `categoryid` bigint(20) NOT NULL,
  `userid` bigint(20) NOT NULL,
  `genre` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '音乐流派',
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否已删除：0-正常，1-已删除（在回收站）',
  `deleted_at` datetime(6) NULL DEFAULT NULL COMMENT '删除时间',
  `deleted_by` bigint(20) NULL DEFAULT NULL COMMENT '删除人ID',
  `retention_period` int(11) NULL DEFAULT 30 COMMENT '保留天数',
  `permanent_delete_time` datetime(6) NULL DEFAULT NULL COMMENT '永久删除时间',
  `play_count` int(11) NOT NULL DEFAULT 0 COMMENT '播放次数',
  PRIMARY KEY (`musicid`) USING BTREE,
  INDEX `FK7yx2yacxhljih6yj9fy62vhr5`(`categoryid` ASC) USING BTREE,
  INDEX `FK2m4su9xuj1c0245wjdda659eq`(`userid` ASC) USING BTREE,
  INDEX `idx_is_deleted`(`is_deleted` ASC) USING BTREE,
  INDEX `idx_deleted_at`(`deleted_at` ASC) USING BTREE,
  INDEX `idx_permanent_delete_time`(`permanent_delete_time` ASC) USING BTREE,
  CONSTRAINT `FK2m4su9xuj1c0245wjdda659eq` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `FK7yx2yacxhljih6yj9fy62vhr5` FOREIGN KEY (`categoryid`) REFERENCES `music_categories` (`categoryid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 15 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for music_tags
-- ----------------------------
DROP TABLE IF EXISTS `music_tags`;
CREATE TABLE `music_tags`  (
  `tagid` bigint(20) NOT NULL AUTO_INCREMENT,
  `tag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `userid` bigint(20) NULL DEFAULT NULL,
  PRIMARY KEY (`tagid`) USING BTREE,
  INDEX `FKk0ikot9qg2w37rc9dyspb461r`(`userid` ASC) USING BTREE,
  CONSTRAINT `FKk0ikot9qg2w37rc9dyspb461r` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for recycle_bin
-- ----------------------------
DROP TABLE IF EXISTS `recycle_bin`;
CREATE TABLE `recycle_bin`  (
  `recycleid` bigint(20) NOT NULL AUTO_INCREMENT,
  `deleted_at` datetime(6) NOT NULL,
  `recovery_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT '恢复状态：0-未恢复，1-已恢复',
  `permanently_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否永久删除：0-否，1-是',
  `permanent_delete_time` datetime(6) NULL DEFAULT NULL COMMENT '永久删除时间',
  `retention_period` int(11) NOT NULL DEFAULT 30 COMMENT '保留天数',
  `deleted_by` bigint(20) NULL DEFAULT NULL COMMENT '删除人ID',
  `musicid` bigint(20) NOT NULL,
  `deleted_note` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '删除备注',
  PRIMARY KEY (`recycleid`) USING BTREE,
  INDEX `FKiwn68b5wwe1fybysj244ued7q`(`deleted_by` ASC) USING BTREE,
  INDEX `FK4ceopkja2jh3ar46nq8j0gaio`(`musicid` ASC) USING BTREE,
  INDEX `idx_recovery_status`(`recovery_status` ASC) USING BTREE,
  INDEX `idx_permanently_deleted`(`permanently_deleted` ASC) USING BTREE,
  INDEX `idx_permanent_delete_time`(`permanent_delete_time` ASC) USING BTREE,
  CONSTRAINT `FK4ceopkja2jh3ar46nq8j0gaio` FOREIGN KEY (`musicid`) REFERENCES `music_resources` (`musicid`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FKiwn68b5wwe1fybysj244ued7q` FOREIGN KEY (`deleted_by`) REFERENCES `users` (`userid`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `userid` bigint(20) NOT NULL AUTO_INCREMENT,
  `avatar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `created_at` datetime(6) NULL DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `updated_at` datetime(6) NULL DEFAULT NULL,
  `verification_status` bit(1) DEFAULT b'0' COMMENT '账户验证状态：0-未验证，1-已验证',
  `is_locked` bit(1) NOT NULL DEFAULT b'0' COMMENT '账户是否被锁定：0-未锁定，1-已锁定',
  `lock_reason` varchar(255) DEFAULT NULL COMMENT '账户锁定原因',
  `lock_time` datetime(6) DEFAULT NULL COMMENT '账户锁定时间',
  `unlock_time` datetime(6) DEFAULT NULL COMMENT '账户解锁时间',
  PRIMARY KEY (`userid`) USING BTREE,
  INDEX `idx_user_locked` (`is_locked`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Initial data for recycle_bin_settings
-- ----------------------------
INSERT INTO `recycle_bin_settings` (`default_retention_days`, `auto_cleanup_enabled`, `auto_cleanup_time`, `notify_before_cleanup`, `notify_hours_before`, `notify_after_cleanup`)
VALUES (30, 1, '03:00', 1, 24, 1);

-- ----------------------------
-- Table structure for recycle_bin_settings
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
-- Records of recycle_bin_settings
-- ----------------------------
INSERT INTO `recycle_bin_settings` (`id`, `default_retention_days`, `auto_cleanup_enabled`, `auto_cleanup_time`)
VALUES (1, 30, 1, '03:00:00');

SET FOREIGN_KEY_CHECKS = 1;
