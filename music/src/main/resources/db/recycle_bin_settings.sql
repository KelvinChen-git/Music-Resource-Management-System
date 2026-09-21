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