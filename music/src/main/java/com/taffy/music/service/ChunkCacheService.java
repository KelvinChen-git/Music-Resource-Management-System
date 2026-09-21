package com.taffy.music.service;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.taffy.music.domain.FileChunk;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * 分片缓存服务
 */
@Slf4j
@Service
public class ChunkCacheService {

    @Autowired
    private FileChunkService fileChunkService;

    // 文件ID -> 分片列表的映射
    private final Map<Long, List<FileChunk>> fileChunksMap = new ConcurrentHashMap<>();
    
    // 文件ID -> 最后更新时间的映射
    private final Cache<Long, LocalDateTime> lastUpdateTimeMap = Caffeine.newBuilder()
            .expireAfterWrite(30, TimeUnit.MINUTES)
            .build();

    // 批量提交的阈值，当缓存中的分片数量达到此值时触发提交
    private static final int BATCH_THRESHOLD = 10;
    
    /**
     * 添加分片到缓存
     * @param fileId 文件ID
     * @param chunk 分片信息
     */
    public void addChunk(Long fileId, FileChunk chunk) {
        fileChunksMap.computeIfAbsent(fileId, k -> new ArrayList<>()).add(chunk);
        lastUpdateTimeMap.put(fileId, LocalDateTime.now());
        
        // 每次分片上传都立即写入数据库（同步持久化）
        try {
            fileChunkService.save(chunk);
        } catch (Exception e) {
            // 若已存在则忽略（如唯一索引冲突），保证幂等
            log.warn("分片[fileId={}, chunkIndex={}]已存在或写入异常: {}", fileId, chunk.getChunkIndex(), e.getMessage());
        }
        
        // 如果达到批量提交阈值，则立即提交
        if (fileChunksMap.get(fileId).size() >= BATCH_THRESHOLD) {
            commitFileChunks(fileId);
        }
    }
    
    /**
     * 获取文件缓存中的分片列表
     * @param fileId 文件ID
     * @return 分片列表
     */
    public List<FileChunk> getCachedChunks(Long fileId) {
        List<FileChunk> chunks = fileChunksMap.get(fileId);
        return chunks != null ? new ArrayList<>(chunks) : Collections.emptyList();
    }
    
    /**
     * 提交指定文件的所有分片
     * @param fileId 文件ID
     */
    public synchronized void commitFileChunks(Long fileId) {
        List<FileChunk> chunks = fileChunksMap.get(fileId);
        if (chunks != null && !chunks.isEmpty()) {
            try {
                log.info("批量提交文件[{}]的{}个分片", fileId, chunks.size());
                fileChunkService.saveBatch(chunks);
                fileChunksMap.remove(fileId);
                lastUpdateTimeMap.invalidate(fileId);
            } catch (Exception e) {
                log.error("批量提交文件[{}]的分片失败", fileId, e);
            }
        }
    }
    
    /**
     * 提交所有缓存中的分片
     */
    public synchronized void commitAllFileChunks() {
        log.info("开始提交所有缓存的分片，当前缓存文件数: {}", fileChunksMap.size());
        for (Long fileId : new ArrayList<>(fileChunksMap.keySet())) {
            commitFileChunks(fileId);
        }
    }
    
    /**
     * 定时提交超时的分片，每分钟检查一次
     */
    @Scheduled(fixedRate = 60000)
    public void scheduledCommit() {
        LocalDateTime now = LocalDateTime.now();
        List<Long> timeoutFileIds = new ArrayList<>();
        
        lastUpdateTimeMap.asMap().forEach((fileId, lastUpdateTime) -> {
            // 如果上次更新时间超过5分钟，则认为超时
            if (lastUpdateTime.plusMinutes(5).isBefore(now)) {
                timeoutFileIds.add(fileId);
            }
        });
        
        for (Long fileId : timeoutFileIds) {
            log.info("文件[{}]的分片上传超时，执行提交", fileId);
            commitFileChunks(fileId);
        }
    }
    
    /**
     * 应用关闭时提交所有缓存
     */
    @PostConstruct
    public void init() {
        // 注册JVM关闭钩子，确保应用关闭时提交所有缓存
        Runtime.getRuntime().addShutdownHook(new Thread(this::commitAllFileChunks));
    }
} 