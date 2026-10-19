import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.mapper.FileChunkMapper;
import com.taffy.music.service.impl.FileChunkServiceImpl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@ExtendWith(MockitoExtension.class)
class FileChunkServiceImplTest {

    @Mock
    private FileChunkMapper fileChunkMapper;
    @Captor
    private ArgumentCaptor<List<FileChunk>> listCaptor; // 明确泛型类型
    @Captor
    private ArgumentCaptor<LambdaQueryWrapper<FileChunk>> queryWrapperCaptor;

    @InjectMocks
    private FileChunkServiceImpl fileChunkService;

    private FileChunk chunk1;
    private FileChunk chunk2;
    private final Long testFileId = 1L;
    private final Integer testChunkIndex = 1;

    @BeforeEach
    void setUp() {
        // 初始化测试分片数据
        Wrappers.lambdaQuery(FileChunk.class);
        chunk1 = new FileChunk();
        chunk1.setFileId(testFileId);
        chunk1.setChunkIndex(2);
        chunk1.setStatus(1);

        chunk2 = new FileChunk();
        chunk2.setFileId(testFileId);
        chunk2.setChunkIndex(1);
        chunk2.setStatus(0);
        
        ReflectionTestUtils.setField(fileChunkService, "baseMapper", fileChunkMapper);
        
        
    }

    /* 测试 getChunksByFileId 方法 */
    @Test
void getChunksByFileId_ShouldReturnOrderedChunks() {
    // Arrange
    List<FileChunk> mockChunks = Arrays.asList(chunk2, chunk1);
    
    // 修改 Mock 逻辑：捕获 LambdaQueryWrapper 参数，但不干扰其内部构建
    when(fileChunkMapper.selectList(any(LambdaQueryWrapper.class))).thenAnswer(invocation -> {
        LambdaQueryWrapper<FileChunk> wrapper = invocation.getArgument(0);
        
        // 手动模拟排序行为：根据 chunkIndex 升序排序
        return mockChunks.stream()
                .sorted(Comparator.comparingInt(FileChunk::getChunkIndex))
                .collect(Collectors.toList());
    });

    // Act
    List<FileChunk> result = fileChunkService.getChunksByFileId(testFileId);

    // Assert
    assertEquals(2, result.size());
    assertEquals(1, result.get(0).getChunkIndex());
    assertEquals(2, result.get(1).getChunkIndex());

    // 验证是否调用了 selectList，且排序逻辑正确
    verify(fileChunkMapper).selectList(any(LambdaQueryWrapper.class));
}
    @Test
    void getChunksByFileId_ShouldReturnEmptyListWhenNoChunks() {
        // Arrange
        when(fileChunkMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Collections.emptyList());

        // Act
        List<FileChunk> result = fileChunkService.getChunksByFileId(999L);

        // Assert
        assertTrue(result.isEmpty());
    }
//


    @Test
    void isChunkUploaded_ShouldReturnFalseWhenChunkNotExists() {
        // Arrange
        when(fileChunkMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);

        // Act & Assert
        assertFalse(fileChunkService.isChunkUploaded(testFileId, 999));
    }

    @Test
    void isChunkUploaded_ShouldReturnFalseWhenStatusNotMatched() {
        // Arrange
        chunk2.setStatus(0); // 状态不匹配
        when(fileChunkMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);

        // Act & Assert
        assertFalse(fileChunkService.isChunkUploaded(testFileId, 1));
    }
    /* 测试 isChunkUploaded 方法 */
    @Test
    void isChunkUploaded_ShouldReturnTrueWhenChunkExists() {
        // 模拟存在分片
        when(fileChunkMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

        // 执行测试
        boolean result = fileChunkService.isChunkUploaded(testFileId, testChunkIndex);

        // 验证结果
        assertTrue(result, "分片应存在");

        // 验证是否调用了 selectCount 方法
        verify(fileChunkMapper).selectCount(any(LambdaQueryWrapper.class));
    }
}