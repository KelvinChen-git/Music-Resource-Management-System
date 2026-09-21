import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import com.github.benmanes.caffeine.cache.Cache;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.service.ChunkCacheService;
import com.taffy.music.service.FileChunkService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ChunkCacheServiceTest {

    @Mock
    private FileChunkService fileChunkService;

    @InjectMocks
    private ChunkCacheService chunkCacheService;

    private static final Long TEST_FILE_ID = 1L;
    private static final FileChunk TEST_CHUNK = new FileChunk();

    @BeforeEach
    void setUp() {
        // 初始化测试分片对象
        TEST_CHUNK.setFileId(TEST_FILE_ID);
        TEST_CHUNK.setChunkIndex(1);
        TEST_CHUNK.setStatus(1);
    }
    // ===================== 反射工具方法 =====================
    /**
     * 获取缓存的分片列表
     */
    @SuppressWarnings("unchecked")
    private List<FileChunk> getCachedChunks(Long fileId) throws Exception {
        Field chunksMapField = ChunkCacheService.class.getDeclaredField("fileChunksMap");
        chunksMapField.setAccessible(true);
        Map<Long, List<FileChunk>> map = (Map<Long, List<FileChunk>>) chunksMapField.get(chunkCacheService);
        return map.get(fileId);
    }

    /**
     * 获取最后更新时间
     */
    private LocalDateTime getLastUpdateTime(Long fileId) throws Exception {
        Cache<Long, LocalDateTime> cache = getLastUpdateTimeCache();
        return cache.getIfPresent(fileId);
    }

    /**
     * 设置最后更新时间（用于模拟超时）
     */
    private void setLastUpdateTime(Long fileId, LocalDateTime time) throws Exception {
        Cache<Long, LocalDateTime> cache = getLastUpdateTimeCache();
        cache.put(fileId, time);
    }

    /**
     * 获取时间戳缓存对象
     */
    @SuppressWarnings("unchecked")
    private Cache<Long, LocalDateTime> getLastUpdateTimeCache() throws Exception {
        Field cacheField = ChunkCacheService.class.getDeclaredField("lastUpdateTimeMap");
        cacheField.setAccessible(true);
        return (Cache<Long, LocalDateTime>) cacheField.get(chunkCacheService);
    }


    /* 测试用例1：添加分片到缓存 */
    @Test
    void addChunk_ShouldAddToCacheAndUpdateTimestamp() throws Exception {
        // 执行操作
        chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);

        // 验证结果
        List<FileChunk> cachedChunks = chunkCacheService.getCachedChunks(TEST_FILE_ID);
        assertEquals(1, cachedChunks.size(), "缓存分片数量应为1");
        assertNotNull(getLastUpdateTime(TEST_FILE_ID), "时间戳应被更新");
    }
    /* 测试用例2：触发批量提交阈值 */
    @Test
void addChunk_ShouldAutoCommitWhenThresholdReached() throws Exception {
    // 添加10个分片（达到阈值）
    for (int i = 0; i < 10; i++) {
        chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);
    }

    // 验证是否触发批量提交
    verify(fileChunkService, times(1)).saveBatch(argThat(list -> 
        list.size() == 10 && 
        list.stream().allMatch(c -> c.getFileId().equals(TEST_FILE_ID))
    ));
    
    // 断言：缓存条目应被移除，返回 null
    assertNull(getCachedChunks(TEST_FILE_ID), "提交后缓存应被移除");
}

    /* 测试用例3：手动提交指定文件 */
    @Test
void commitFileChunks_ShouldClearCache() throws Exception {
    // ============== 准备数据 ==============
    chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);
    chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);

    // ============== 执行提交 ==============
    chunkCacheService.commitFileChunks(TEST_FILE_ID);

    // ============== 验证结果 ==============
    // 1. 捕获保存的批次参数
    ArgumentCaptor<List<FileChunk>> captor = ArgumentCaptor.forClass(List.class);
    verify(fileChunkService).saveBatch(captor.capture());
    
    // 2. 获取实际传递的列表
    List<FileChunk> savedChunks = captor.getValue();
    
    // 3. 独立验证列表内容
    assertNotNull(savedChunks, "保存的分片列表不应为 null");
    assertEquals(2, savedChunks.size(), "应保存2个分片");
    assertEquals(1, savedChunks.get(0).getChunkIndex(), "第一个分片的索引应为1");
    
    // 4. 验证缓存已清空
    assertNull(getCachedChunks(TEST_FILE_ID), "提交后应移除缓存条目");
}

    /* 测试用例4：定时任务提交超时分片 */
    @Test
    void scheduledCommit_ShouldHandleTimeout() throws Exception {
        // 设置测试数据
        chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);
        setLastUpdateTime(TEST_FILE_ID, LocalDateTime.now().minusMinutes(6));

        // 直接触发定时任务
        chunkCacheService.scheduledCommit();
        TimeUnit.MILLISECONDS.sleep(100); // 确保异步执行完成

        // 验证结果
        verify(fileChunkService).saveBatch(anyList());
        assertNull(getCachedChunks(TEST_FILE_ID), "提交后应清空缓存");
    }

    /* 测试用例5：关闭钩子提交所有缓存 */
    @Test
    void shutdownHook_ShouldCommitAll() throws Exception {
        // 添加多文件分片
        chunkCacheService.addChunk(TEST_FILE_ID, TEST_CHUNK);
        chunkCacheService.addChunk(2L, TEST_CHUNK);
        chunkCacheService.addChunk(3L, TEST_CHUNK);

        // 手动触发关闭钩子
        Thread shutdownHook = new Thread(chunkCacheService::commitAllFileChunks);
        shutdownHook.start();
        shutdownHook.join();

        // 验证提交次数
        verify(fileChunkService, times(3)).saveBatch(anyList());
    }
}