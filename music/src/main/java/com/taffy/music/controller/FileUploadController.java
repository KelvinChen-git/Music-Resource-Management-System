package com.taffy.music.controller;

import cn.hutool.core.io.FileUtil;
import jakarta.servlet.http.HttpServletResponse;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.service.UploadIntegrityService;
import com.taffy.music.service.UploadAccessService;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.transaction.annotation.Transactional;
import com.taffy.music.service.MediaAccessService;
import com.taffy.music.utils.MediaResponses;
import com.taffy.music.service.FileChunkService;
import com.taffy.music.service.FileUploadService;
import com.taffy.music.utils.RateLimiter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.vo.FileCreateVO;
import com.taffy.music.vo.FileCheckVO;
import com.taffy.music.vo.FileMergeVO;
import com.taffy.music.vo.FileUploadStatusVO;
import com.taffy.music.common.Result;
import cn.hutool.crypto.digest.DigestUtil;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 文件上传控制器
 */
@Slf4j
@RestController
@RequestMapping("/file")
public class FileUploadController {

    @Autowired
    private FileUploadService fileUploadService;

    @Autowired
    private UploadAccessService uploadAccessService;

    @Autowired
    private MediaAccessService mediaAccessService;

    @Autowired
    private FileChunkService fileChunkService;

    @Autowired
    private UploadIntegrityService uploadIntegrityService;

    @Autowired
    private UploadProperties uploadProperties;

    /**
     * 生成唯一文件名
     * @param originalFilename 原始文件名
     * @return 新的文件名
     */
    private String generateUniqueFileName(String originalFilename) {
        // 获取文件扩展名
        String extension = "";
        int lastDotIndex = originalFilename.lastIndexOf(".");
        if (lastDotIndex > 0) {
            extension = originalFilename.substring(lastDotIndex);
        }
        
        // 生成时间戳
        String timestamp = LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        
        // 生成6位随机字符串
        String randomStr = cn.hutool.core.util.RandomUtil.randomString(6);
        
        // 组合新文件名：时间戳_随机字符串.扩展名
        return timestamp + "_" + randomStr + extension;
    }

    /**
     * 创建文件记录
     */
    @PostMapping("/create")
    public Result<FileUpload> createFile(@RequestBody FileCreateVO vo) {
        try {
            Long owner = uploadAccessService.requireViewer().getUserid();
            if (vo.getFileName() == null || !vo.getFileName().contains(".")
                    || vo.getFileSize() == null || vo.getFileSize() <= 0
                    || vo.getChunkCount() == null || vo.getChunkCount() <= 0
                    || vo.getChunkCount() > vo.getFileSize()
                    || !UploadIntegrityService.validMd5(vo.getFileMd5())) {
                return Result.error("文件名、大小、分片数量或MD5无效");
            }
            // 获取文件扩展名
            String fileType = vo.getFileName().substring(vo.getFileName().lastIndexOf(".") + 1).toLowerCase();
            
            // 验证文件类型
            List<String> allowedTypes = uploadProperties.getAllowedTypeList();
            if (!allowedTypes.contains(fileType)) {
                return Result.error("不支持的文件类型：" + fileType + "，允许的类型：" + String.join(",", allowedTypes));
            }

            FileUpload fileUpload = new FileUpload();
            fileUpload.setOwnerUserId(owner);
            fileUpload.setFileName(vo.getFileName());
            fileUpload.setFileSize(vo.getFileSize());
            fileUpload.setFileMd5(vo.getFileMd5().toLowerCase(java.util.Locale.ROOT));
            fileUpload.setChunkCount(vo.getChunkCount());
            fileUpload.setStatus(0);
            fileUpload.setUploadedChunks(0);
            fileUpload.setCreateTime(LocalDateTime.now());
            fileUpload.setUpdateTime(LocalDateTime.now());
            fileUpload.setFilePath("temp/" + vo.getFileMd5());
            fileUpload.setFileType(fileType);
            fileUpload.setChunkSize(uploadProperties.getChunkSize().intValue());
            
            if (!fileUploadService.save(fileUpload)) return Result.error("创建文件记录失败");
            return Result.success(fileUpload);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("创建文件记录失败", e);
            return Result.error("创建文件记录失败");
        }
    }

    /**
     * 检查文件是否已存在（秒传）
     */
    @GetMapping("/check")
    public Result<FileCheckVO> checkFile(@RequestParam String fileMd5) {
        uploadAccessService.requireViewer();
        FileUpload fileUpload = fileUploadService.getByFileMd5(fileMd5);
        FileCheckVO vo = new FileCheckVO();
        if (fileUpload != null && fileUpload.getStatus() == 1) {
            // 只有当文件状态为1（上传完成）时才允许秒传
            vo.setExists(true);
            vo.setFileId(fileUpload.getId());
            vo.setFilePath(fileUpload.getFilePath());
        } else if (fileUpload != null) {
            // 文件记录存在但未上传完成，返回文件ID以支持断点续传
            vo.setExists(false);
            vo.setFileId(fileUpload.getId());
            log.info("文件[{}]存在未完成的上传记录，支持断点续传", fileMd5);
        } else {
            vo.setExists(false);
        }
        return Result.success(vo);
    }

    /**
     * 上传分片
     */
    @PostMapping("/chunk")
    public Result<String> uploadChunk(
            @RequestParam Long fileId,
            @RequestParam Integer chunkIndex,
            @RequestParam MultipartFile chunk,
            @RequestParam String chunkMd5) {
        try {
            uploadIntegrityService.uploadChunk(fileId, chunkIndex, chunk, chunkMd5);
            return Result.success("分片上传成功");
        } catch (IllegalArgumentException e) {
            return Result.error(e.getMessage());
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("分片上传失败", e);
            return Result.error("分片上传失败");
        }
    }

    /** 合并经过持久化和完整性校验的分片。 */
    @PostMapping("/merge")
    public Result<FileMergeVO> mergeChunks(@RequestParam Long fileId) {
        try {
            FileMergeVO vo = new FileMergeVO();
            vo.setFilePath(uploadIntegrityService.merge(fileId));
            return Result.success("文件合并成功", vo);
        } catch (IllegalArgumentException e) {
            return Result.error(e.getMessage());
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("文件合并失败", e);
            return Result.error("文件合并失败");
        }
    }

    /**
     * 获取文件的缺失分片
     */
    @GetMapping("/missing-chunks")
    public Result<List<Integer>> getMissingChunks(@RequestParam Long fileId) {
        try {
            // 获取文件信息
            FileUpload fileUpload = uploadAccessService.requireOwned(fileId);
            if (fileUpload == null) {
                return Result.error("文件不存在");
            }

            // Successful persisted records are the only source of resumable progress.
            List<FileChunk> uploadedChunks = fileChunkService.getChunksByFileId(fileId).stream()
                .filter(c -> Integer.valueOf(1).equals(c.getStatus())
                    && c.getChunkIndex() >= 0 && c.getChunkIndex() < fileUpload.getChunkCount())
                .collect(Collectors.toList());

            // 获取已上传的分片索引集合
            Set<Integer> uploadedIndexes = uploadedChunks.stream()
                .map(FileChunk::getChunkIndex)
                .collect(Collectors.toSet());
            
            // 查找缺失的分片
            List<Integer> missingChunks = new ArrayList<>();
            for (int i = 0; i < fileUpload.getChunkCount(); i++) {
                if (!uploadedIndexes.contains(i)) {
                    missingChunks.add(i);
                }
            }
            
            log.info("文件[{}]共{}个分片，已上传{}个分片，缺失{}个分片", 
                    fileId, fileUpload.getChunkCount(), uploadedChunks.size(), missingChunks.size());
            
            return Result.success(missingChunks);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("获取缺失分片失败", e);
            return Result.error("获取缺失分片失败：" + e.getMessage());
        }
    }

    /**
     * 获取文件列表
     */
    @GetMapping("/list")
    public Result<Page<FileUpload>> getFileList(
            @RequestParam(value = "fileName", required = false) String fileName,
            @RequestParam(value = "fileType", required = false) String fileType,
            @RequestParam(value = "status", required = false) Integer status,
            @RequestParam(value = "current", defaultValue = "1") Long current,
            @RequestParam(value = "pageSize", defaultValue = "10") Long pageSize,
            @RequestParam(value = "orderBy", required = false, defaultValue = "createTime") String orderBy,
            @RequestParam(value = "orderType", required = false, defaultValue = "desc") String orderType) {
        try {
            final long MAX_PAGE_SIZE = 20;
            if (pageSize > MAX_PAGE_SIZE) {
                pageSize = MAX_PAGE_SIZE;
            }
            // 使用 QueryWrapper
            QueryWrapper<FileUpload> queryWrapper = new QueryWrapper<>();
            queryWrapper.eq("owner_user_id", uploadAccessService.requireViewer().getUserid());
            queryWrapper.eq("deleted", 0); // 添加删除标记条件
            if (fileName != null && !fileName.trim().isEmpty()) {
                queryWrapper.like("file_name", fileName.trim());
            }
            if (fileType != null && !fileType.trim().isEmpty()) {
                queryWrapper.eq("file_type", fileType.trim());
            }
            if (status != null) {
                queryWrapper.eq("status", status);
            }
            // 动态排序逻辑
            boolean isAsc = "asc".equalsIgnoreCase(orderType);
            // Map UI sort keys to fixed SQL identifiers.
            java.util.Map<String, String> columns = java.util.Map.of(
                    "createTime", "create_time", "completeTime", "complete_time", "fileName", "file_name",
                    "fileType", "file_type", "fileSize", "file_size", "status", "status");
            String column = columns.getOrDefault(orderBy, "create_time");
            pageSize = Math.max(1L, pageSize);
            current = Math.max(1L, current);
            // 添加白名单校验，防止SQL注入
            queryWrapper.orderBy(true, isAsc, column);
            Page<FileUpload> page = new Page<>(current, pageSize, true);
            Page<FileUpload> result = fileUploadService.page(page, queryWrapper);
            return Result.success(result);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("获取文件列表失败", e);
            return Result.error("获取文件列表失败");
        }
    }

    /**
     * 删除文件
     */
    @Transactional(rollbackFor = Exception.class)
    @DeleteMapping("/{fileId}")
    public Result<Void> deleteFile(@PathVariable("fileId") Long fileId) {
        FileUpload upload = uploadAccessService.requireOwnedLocked(fileId);
        uploadAccessService.requireUnreferenced(upload);
        // Retain bytes/chunks: no destructive filesystem work before DB commit, and legacy
        // shared paths must not destroy another upload or a recoverable music resource.
        if (!fileUploadService.removeById(fileId)) throw new IllegalStateException("删除文件记录失败");
        return Result.success();
    }

    /**
     * 获取文件详情
     */
    @GetMapping("/{fileId}")
    public Result<FileUpload> getFileDetail(@PathVariable Long fileId) {
        try {
            FileUpload fileUpload = uploadAccessService.requireOwned(fileId);
            if (fileUpload == null) {
                return Result.error("文件不存在");
            }
            return Result.success(fileUpload);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("获取文件详情失败", e);
            return Result.error("获取文件详情失败");
        }
    }

    /*
     * 测试控制器返回一个字符串
     */
    @GetMapping("/test")
    public Result<String> test() {
        return Result.success("测试成功");
    }

    /**
     * 下载文件
     */
    @GetMapping("/download/{fileId}")
    public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> downloadFile(@PathVariable Long fileId) {
        FileUpload upload = mediaAccessService.requireUpload(fileId);
        return MediaResponses.file(mediaAccessService.requirePath(upload.getFilePath()), upload.getFileName(),
                org.springframework.http.MediaType.APPLICATION_OCTET_STREAM, true, uploadProperties.getDownloadRateLimit());
    }

    /**
     * 获取文件上传状态
     */
    @GetMapping("/status/{fileId}")
    public Result<FileUploadStatusVO> getUploadStatus(@PathVariable Long fileId) {
        try {
            // 获取文件信息
            FileUpload fileUpload = uploadAccessService.requireOwned(fileId);
            if (fileUpload == null) {
                return Result.error("文件不存在");
            }

            // Successful persisted records are the only source of resumable progress.
            List<FileChunk> uploadedChunks = fileChunkService.getChunksByFileId(fileId).stream()
                .filter(c -> Integer.valueOf(1).equals(c.getStatus())
                    && c.getChunkIndex() >= 0 && c.getChunkIndex() < fileUpload.getChunkCount())
                .collect(Collectors.toList());

            // 获取已上传的分片索引集合
            List<Integer> uploadedIndexes = uploadedChunks.stream()
                .map(FileChunk::getChunkIndex)
                .sorted()
                .collect(Collectors.toList());
            
            // 查找缺失的分片
            List<Integer> missingChunks = new ArrayList<>();
            for (int i = 0; i < fileUpload.getChunkCount(); i++) {
                if (!uploadedIndexes.contains(i)) {
                    missingChunks.add(i);
                }
            }
            
            // 构建返回对象
            FileUploadStatusVO vo = new FileUploadStatusVO();
            vo.setFileId(fileUpload.getId());
            vo.setFileName(fileUpload.getFileName());
            vo.setFileSize(fileUpload.getFileSize());
            vo.setFileType(fileUpload.getFileType());
            vo.setChunkCount(fileUpload.getChunkCount());
            vo.setUploadedChunks(uploadedChunks.size());
            vo.setStatus(fileUpload.getStatus());
            // 计算上传进度
            vo.setProgress(fileUpload.getChunkCount() > 0 
                ? (int) ((double) uploadedChunks.size() / fileUpload.getChunkCount() * 100)
                : 0);
            vo.setUploadedChunkIndexes(uploadedIndexes);
            vo.setMissingChunkIndexes(missingChunks);
            vo.setCreateTime(fileUpload.getCreateTime());
            vo.setUpdateTime(fileUpload.getUpdateTime());
            
            return Result.success(vo);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("获取文件上传状态失败", e);
            return Result.error("获取文件上传状态失败：" + e.getMessage());
        }
    }

    /**
     * 普通文件上传接口
     * @param file 上传的文件
     * @return 包含文件信息的结果对象
     */
    @PostMapping("/upload")
    public Result<FileUpload> uploadSingleFile(@RequestParam("file") MultipartFile file) {
        try {
            Long owner = uploadAccessService.requireViewer().getUserid();
            // 1. 获取文件信息
            String originalFilename = file.getOriginalFilename();
            long fileSize = file.getSize();

            if (originalFilename == null || originalFilename.trim().isEmpty()) {
                return Result.error("文件名不能为空");
            }
            if (fileSize == 0) {
                return Result.error("文件不能为空");
            }

            // 2. 验证文件类型
            String fileType = "";
            int lastDotIndex = originalFilename.lastIndexOf(".");
            if (lastDotIndex > 0 && lastDotIndex < originalFilename.length() - 1) {
                fileType = originalFilename.substring(lastDotIndex + 1).toLowerCase();
            } else {
                 return Result.error("无法识别的文件类型");
            }

            List<String> allowedTypes = uploadProperties.getAllowedTypeList();
            if (!allowedTypes.contains(fileType)) {
                log.warn("不支持的文件类型: {}, 允许的类型: {}", fileType, allowedTypes);
                return Result.error("不支持的文件类型：" + fileType + "，允许的类型：" + String.join(",", allowedTypes));
            }

            // 3. 生成存储细节
            String uniqueFileName = generateUniqueFileName(originalFilename);
            String dateDir = LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String targetDir = uploadProperties.getPath() + "/" + dateDir;
            String relativePath = dateDir + "/" + uniqueFileName;
            String targetPath = uploadProperties.getPath() + "/" + relativePath;

            // 4. 创建目录
            FileUtil.mkdir(targetDir);

            // 5. 保存文件
            File targetFile = new File(targetPath);
            RateLimiter limiter = new RateLimiter(uploadProperties.getUploadRateLimit());
            try (InputStream input = file.getInputStream();
                 OutputStream output = Files.newOutputStream(targetFile.toPath())) {
                limiter.copy(input, output, new byte[8192]); // 使用 8KB 缓冲区
            } catch (IOException e) {
                 log.error("保存文件时发生IO异常", e);
                 // 尝试删除可能创建的不完整文件
                 FileUtil.del(targetFile);
                 return Result.error("文件保存失败: " + e.getMessage());
            }

            // 6. 计算文件 MD5
            String fileMd5;
            try {
                fileMd5 = DigestUtil.md5Hex(targetFile);
            } catch (Exception e) {
                log.error("计算文件MD5失败", e);
                // 删除已保存的文件，因为无法验证其完整性
                FileUtil.del(targetFile);
                return Result.error("文件MD5计算失败: " + e.getMessage());
            }

            // 7. 创建数据库记录
            FileUpload fileUpload = new FileUpload();
            fileUpload.setOwnerUserId(owner);
            fileUpload.setFileName(originalFilename);
            fileUpload.setFileSize(fileSize);
            fileUpload.setFileMd5(fileMd5);
            fileUpload.setFilePath(relativePath);
            fileUpload.setFileType(fileType);
            fileUpload.setStatus(1); // 1 表示已完成
            fileUpload.setChunkCount(1); // 普通上传视为1个块
            fileUpload.setUploadedChunks(1);
            fileUpload.setChunkSize((int) fileSize); // 块大小即文件大小
            fileUpload.setCreateTime(LocalDateTime.now());
            fileUpload.setUpdateTime(LocalDateTime.now());
            fileUpload.setCompleteTime(LocalDateTime.now());

            try {
                if (!fileUploadService.save(fileUpload)) throw new IllegalStateException("创建文件记录失败");
            } catch (RuntimeException failure) {
                FileUtil.del(targetFile);
                throw failure;
            }

            log.info("文件上传成功: {}, 路径: {}", originalFilename, relativePath);
            // 8. 返回成功结果
            return Result.success(fileUpload);

        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.error("普通文件上传处理失败", e);
            return Result.error("文件上传失败: " + e.getMessage());
        }
    }
}