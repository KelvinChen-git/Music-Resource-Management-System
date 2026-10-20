package com.taffy.music.service;

import cn.hutool.crypto.digest.DigestUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.utils.RateLimiter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

/** Database-backed resumability: no deferred writes or process-local chunk cache. */
@Slf4j
@Service
public class UploadIntegrityService {
    private final FileUploadService uploads;
    private final FileChunkService chunks;
    private final UploadProperties properties;
    private final UploadAccessService access;

    public UploadIntegrityService(FileUploadService uploads, FileChunkService chunks, UploadProperties properties, UploadAccessService access) {
        this.uploads = uploads;
        this.chunks = chunks;
        this.properties = properties;
        this.access = access;
    }

    public static boolean validMd5(String value) {
        return value != null && value.matches("[0-9a-fA-F]{32}");
    }

    private FileUpload lockUpload(Long fileId) {
        return access.requireOwnedLocked(fileId);
    }

    @Transactional(rollbackFor = Exception.class)
    public void uploadChunk(Long fileId, Integer index, MultipartFile input, String expectedMd5) throws IOException {
        FileUpload upload = lockUpload(fileId);
        if (!Integer.valueOf(0).equals(upload.getStatus())) throw new IllegalArgumentException("文件不是上传中状态");
        if (index == null || index < 0 || index >= upload.getChunkCount())
            throw new IllegalArgumentException("分片索引无效");
        if (!validMd5(expectedMd5) || input == null || input.isEmpty()
                || input.getSize() > Integer.MAX_VALUE || input.getSize() > upload.getFileSize())
            throw new IllegalArgumentException("分片大小或MD5无效");

        List<FileChunk> existing = chunks.getChunksByFileIdForUpdate(fileId);
        FileChunk previous = existing.stream().filter(c -> index.equals(c.getChunkIndex())).findFirst().orElse(null);
        Path directory = Path.of(properties.getTempPath(), fileId.toString());
        Files.createDirectories(directory);
        Path candidate = Files.createTempFile(directory, index + "-", ".chunk");
        boolean accepted = false;
        try {
            try (var source = input.getInputStream(); var target = new FileOutputStream(candidate.toFile())) {
                new RateLimiter(properties.getUploadRateLimit()).copy(source, target, new byte[8192]);
                target.getFD().sync();
            }
            String actualMd5 = DigestUtil.md5Hex(candidate.toFile());
            long size = Files.size(candidate);
            if (size != input.getSize() || !actualMd5.equalsIgnoreCase(expectedMd5))
                throw new IllegalArgumentException("分片MD5或大小不匹配");
            if (previous != null && (!actualMd5.equalsIgnoreCase(previous.getChunkMd5())
                    || size != previous.getChunkSize()))
                throw new IllegalArgumentException("分片内容与已接收内容冲突");

            if (previous == null || !Integer.valueOf(1).equals(previous.getStatus()) || !validChunkFile(previous)) {
                FileChunk record = previous == null ? new FileChunk() : previous;
                String oldPath = record.getChunkPath();
                record.setFileId(fileId);
                record.setChunkIndex(index);
                record.setChunkMd5(actualMd5);
                record.setChunkSize(Math.toIntExact(size));
                record.setChunkPath(candidate.toString());
                record.setStatus(1);
                if (!(previous == null ? chunks.save(record) : chunks.updateById(record)))
                    throw new IllegalStateException("分片记录保存失败");
                if (oldPath != null) afterCommit(() -> delete(Path.of(oldPath)));
                cleanupOnRollback(candidate);
                accepted = true;
            }
            // Count persisted rows instead of incrementing a stale client/process value.
            long count = chunks.getChunksByFileIdForUpdate(fileId).stream()
                    .filter(c -> Integer.valueOf(1).equals(c.getStatus())).count();
            upload.setUploadedChunks(Math.toIntExact(count));
            upload.setUpdateTime(LocalDateTime.now());
            if (!uploads.updateById(upload)) throw new IllegalStateException("上传计数保存失败");
        } catch (IOException | RuntimeException e) {
            delete(candidate);
            throw e;
        } finally {
            if (!accepted) delete(candidate); // duplicate request or validation failure
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public String merge(Long fileId) throws IOException {
        FileUpload upload = lockUpload(fileId);
        if (Integer.valueOf(1).equals(upload.getStatus())) {
            File complete = Path.of(properties.getPath(), upload.getFilePath()).toFile();
            if (!complete.isFile() || complete.length() != upload.getFileSize()
                    || !DigestUtil.md5Hex(complete).equalsIgnoreCase(upload.getFileMd5()))
                throw new IllegalArgumentException("已完成文件缺失或损坏");
            return upload.getFilePath();
        }
        if (!Integer.valueOf(0).equals(upload.getStatus())) throw new IllegalArgumentException("文件不是上传中状态");
        List<FileChunk> records = chunks.getChunksByFileIdForUpdate(fileId).stream()
                .sorted(Comparator.comparingInt(FileChunk::getChunkIndex)).toList();
        if (records.size() != upload.getChunkCount()) throw new IllegalArgumentException("分片未上传完成");
        for (int i = 0; i < records.size(); i++) {
            FileChunk record = records.get(i);
            if (record.getChunkIndex() != i || !Integer.valueOf(1).equals(record.getStatus()) || !validChunkFile(record))
                throw new IllegalArgumentException("分片缺失、损坏或索引无效，请重传原分片");
        }
        String extension = upload.getFileName().substring(upload.getFileName().lastIndexOf('.'));
        String relativePath = LocalDate.now() + "/" + UUID.randomUUID() + extension;
        Path target = Path.of(properties.getPath(), relativePath);
        Files.createDirectories(target.getParent());
        boolean accepted = false;
        try {
            try (var output = new FileOutputStream(target.toFile())) {
                for (FileChunk record : records) Files.copy(Path.of(record.getChunkPath()), output);
                output.getFD().sync();
            }
            if (Files.size(target) != upload.getFileSize()
                    || !DigestUtil.md5Hex(target.toFile()).equalsIgnoreCase(upload.getFileMd5()))
                throw new IllegalArgumentException("合并文件MD5或大小不匹配");
            upload.setFilePath(relativePath);
            upload.setStatus(1);
            upload.setUploadedChunks(records.size());
            upload.setCompleteTime(LocalDateTime.now());
            upload.setUpdateTime(LocalDateTime.now());
            if (!uploads.updateById(upload)) throw new IllegalStateException("合并结果保存失败");
            cleanupOnRollback(target);
            afterCommit(() -> records.forEach(c -> delete(Path.of(c.getChunkPath()))));
            accepted = true;
            return relativePath;
        } finally {
            if (!accepted) delete(target);
        }
    }

    private boolean validChunkFile(FileChunk chunk) {
        File file = new File(chunk.getChunkPath());
        return file.isFile() && file.length() == chunk.getChunkSize()
                && DigestUtil.md5Hex(file).equalsIgnoreCase(chunk.getChunkMd5());
    }

    private void cleanupOnRollback(Path path) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCompletion(int status) {
                    if (status == STATUS_ROLLED_BACK) delete(path);
                }
            });
        }
    }

    private void afterCommit(Runnable action) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { action.run(); }
            });
        } else action.run(); // direct unit-test invocation; production always uses transactional proxy
    }

    private void delete(Path path) {
        try { Files.deleteIfExists(path); }
        catch (IOException e) { log.warn("无法清理上传临时文件 {}", path, e); }
    }
}
