-- 添加测试用回收站数据
-- 1. 模拟几个处于正常状态的音乐资源
INSERT INTO `music_resources` (`title`, `artist`, `album`, `genre`, `format`, `file_path`, `file_size`, `upload_time`, `categoryid`, `userid`, `approval_status`, `is_deleted`)
VALUES
('Perfect', 'Ed Sheeran', 'Divide', 'Pop', 'mp3', '/music/ed_sheeran_perfect.mp3', 8192000, NOW(), 1, 1, 'approved', 0),
('Shape of You', 'Ed Sheeran', 'Divide', 'Pop', 'mp3', '/music/ed_sheeran_shape_of_you.mp3', 7168000, NOW(), 1, 1, 'approved', 0),
('Thriller', 'Michael Jackson', 'Thriller', 'Pop', 'mp3', '/music/michael_jackson_thriller.mp3', 9216000, NOW(), 1, 2, 'approved', 0);

-- 2. 模拟几个处于已删除状态的音乐资源（软删除）
-- 2.1 一个刚刚删除的音乐资源
INSERT INTO `music_resources` (
  `title`, `artist`, `album`, `genre`, `format`, `file_path`, `file_size`, 
  `upload_time`, `categoryid`, `userid`, `approval_status`, 
  `is_deleted`, `deleted_at`, `deleted_by`, `retention_period`, `permanent_delete_time`
)
VALUES (
  'Bad Romance', 'Lady Gaga', 'The Fame Monster', 'Pop', 'mp3', '/music/lady_gaga_bad_romance.mp3', 
  8388608, DATE_SUB(NOW(), INTERVAL 1 DAY), 1, 2, 'approved', 
  1, DATE_SUB(NOW(), INTERVAL 1 DAY), 1, 30, DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 30 DAY)
);

-- 2.2 一个即将被永久删除的音乐资源（还剩3天）
INSERT INTO `music_resources` (
  `title`, `artist`, `album`, `genre`, `format`, `file_path`, `file_size`, 
  `upload_time`, `categoryid`, `userid`, `approval_status`, 
  `is_deleted`, `deleted_at`, `deleted_by`, `retention_period`, `permanent_delete_time`
)
VALUES (
  'Bohemian Rhapsody', 'Queen', 'A Night at the Opera', 'Rock', 'mp3', '/music/queen_bohemian_rhapsody.mp3', 
  10485760, DATE_SUB(NOW(), INTERVAL 30 DAY), 2, 3, 'approved', 
  1, DATE_SUB(NOW(), INTERVAL 27 DAY), 2, 30, DATE_ADD(NOW(), INTERVAL 3 DAY)
);

-- 2.3 一个删除时间适中的音乐资源（还剩15天）
INSERT INTO `music_resources` (
  `title`, `artist`, `album`, `genre`, `format`, `file_path`, `file_size`, 
  `upload_time`, `categoryid`, `userid`, `approval_status`, 
  `is_deleted`, `deleted_at`, `deleted_by`, `retention_period`, `permanent_delete_time`
)
VALUES (
  'Billie Jean', 'Michael Jackson', 'Thriller', 'Pop', 'mp3', '/music/michael_jackson_billie_jean.mp3', 
  7340032, DATE_SUB(NOW(), INTERVAL 45 DAY), 1, 1, 'approved', 
  1, DATE_SUB(NOW(), INTERVAL 15 DAY), 1, 30, DATE_ADD(NOW(), INTERVAL 15 DAY)
);

-- 3. 添加对应的回收站记录
-- 3.1 刚刚删除的记录
INSERT INTO `recycle_bin` (
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  `recovery_status`, `permanently_deleted`, `permanent_delete_time`, `deleted_note`
)
SELECT 
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  0, 0, `permanent_delete_time`, 'No longer needed'
FROM `music_resources` 
WHERE `title` = 'Bad Romance' AND `is_deleted` = 1;

-- 3.2 即将被永久删除的记录
INSERT INTO `recycle_bin` (
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  `recovery_status`, `permanently_deleted`, `permanent_delete_time`, `deleted_note`
)
SELECT 
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  0, 0, `permanent_delete_time`, 'Duplicate file'
FROM `music_resources` 
WHERE `title` = 'Bohemian Rhapsody' AND `is_deleted` = 1;

-- 3.3 删除时间适中的记录
INSERT INTO `recycle_bin` (
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  `recovery_status`, `permanently_deleted`, `permanent_delete_time`, `deleted_note`
)
SELECT 
  `deleted_at`, `deleted_by`, `musicid`, `retention_period`, 
  0, 0, `permanent_delete_time`, 'Removed by mistake'
FROM `music_resources` 
WHERE `title` = 'Billie Jean' AND `is_deleted` = 1; 