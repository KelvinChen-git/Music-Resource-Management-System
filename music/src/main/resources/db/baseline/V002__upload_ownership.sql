-- Additive migration; existing rows deliberately retain NULL ownership.
-- Run through scripts/dev.py migrate-uploads for isolated development slots.
-- V001 is not modified and no owner is inferred from MD5 or resource references.
ALTER TABLE file_upload
  ADD COLUMN owner_user_id BIGINT NULL DEFAULT NULL COMMENT 'Persisted uploader; NULL means quarantined legacy record',
  ADD INDEX idx_upload_owner_md5 (owner_user_id, file_md5, deleted);
