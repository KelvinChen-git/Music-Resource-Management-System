import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.mapper.FileUploadMapper;
import com.taffy.music.service.impl.FileUploadServiceImpl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FileUploadServiceImplTest {

    @Mock
    private FileUploadMapper fileUploadMapper;

    @Spy
    private FileUploadServiceImpl fileUploadService;

    private FileUpload testFileUpload;

    @BeforeEach
    void setUp() {
        // 1. 初始化测试数据
        testFileUpload = new FileUpload();
        testFileUpload.setId(1L);
        testFileUpload.setFileName("test.mp4");
        testFileUpload.setFileMd5("d41d8cd98f00b204e9800998ecf8427e");
        testFileUpload.setFilePath("/uploads/test.mp4");
        testFileUpload.setStatus(0);
        testFileUpload.setUploadedChunks(3);
        testFileUpload.setChunkCount(10);

        // 2. 初始化服务实例
        fileUploadService = new FileUploadServiceImpl();
        
        // 3. 使用Spring测试工具注入mock依赖
        ReflectionTestUtils.setField(fileUploadService, "baseMapper", fileUploadMapper);
    }

    @Test
void getByFileMd5_ShouldReturnFileUpload_WhenExists() {
    // Arrange
    String md5 = "d41d8cd98f00b204e9800998ecf8427e";
    when(fileUploadMapper.selectOne(any(LambdaQueryWrapper.class), anyBoolean()))
        .thenReturn(testFileUpload);

    // Act
    FileUpload result = fileUploadService.getByFileMd5(md5);

    // Assert
    assertNotNull(result);
    assertEquals(md5, result.getFileMd5());
    verify(fileUploadMapper).selectOne(any(LambdaQueryWrapper.class), anyBoolean());
}
//
    @Test
    void updateStatus_ShouldReturnTrue_WhenSuccess() {
        // Arrange
        when(fileUploadMapper.updateById(any(FileUpload.class))).thenReturn(1);

        // Act
        boolean result = fileUploadService.updateStatus(1L, 1);

        // Assert
        assertTrue(result);
        verify(fileUploadMapper).updateById(argThat(file -> 
            file.getId() == 1L && file.getStatus() == 1
        ));
    }
//
    @Test
    void updateStatus_ShouldSetCompleteTime_WhenStatusIsComplete() {
        // Arrange
        when(fileUploadMapper.updateById(any(FileUpload.class))).thenReturn(1);

        // Act
        fileUploadService.updateStatus(1L, 1);

        // Assert
        verify(fileUploadMapper).updateById(argThat(file -> 
            file.getStatus() == 1 && file.getCompleteTime() != null
        ));
    }
//
    @Test
    void incrementUploadedChunks_ShouldIncrementCount_WhenSuccess() {
        // Arrange
        FileUpload existing = new FileUpload();
        existing.setUploadedChunks(3);
        
        when(fileUploadMapper.selectById(1L)).thenReturn(existing);
        when(fileUploadMapper.updateById(any(FileUpload.class))).thenReturn(1);

        // Act
        boolean result = fileUploadService.incrementUploadedChunks(1L);

        // Assert
        assertTrue(result);
        verify(fileUploadMapper).updateById(argThat(file -> 
            file.getUploadedChunks() == 4
        ));
    }

    @Test
void getByFilePath_ShouldReturnFileUpload_WhenExists() {
    // Arrange
    String path = "/uploads/test.mp4";
    when(fileUploadMapper.selectOne(any(LambdaQueryWrapper.class), anyBoolean()))
        .thenReturn(testFileUpload);

    // Act
    FileUpload result = fileUploadService.getByFilePath(path);

    // Assert
    assertNotNull(result);
    assertEquals(path, result.getFilePath());
    verify(fileUploadMapper).selectOne(any(LambdaQueryWrapper.class), anyBoolean());
}

@Test
void incrementUploadedChunks_ShouldReturnFalse_WhenFileNotFound() {
    when(fileUploadMapper.selectById(1L)).thenReturn(null);
    
    boolean result = fileUploadService.incrementUploadedChunks(1L);
    
    assertFalse(result);
    verify(fileUploadMapper, never()).updateById(any());
}
@Test
void incrementUploadedChunks_ShouldReturnTrue_WhenFileExists() {
    // 模拟存在的文件对象
    FileUpload mockFile = new FileUpload();
    mockFile.setId(1L);
    mockFile.setUploadedChunks(5);
    
    // 模拟 selectById 返回存在的对象
    when(fileUploadMapper.selectById(1L)).thenReturn(mockFile);
    // 模拟 updateById 返回受影响行数 1（表示成功）
    when(fileUploadMapper.updateById(mockFile)).thenReturn(1); // 改为 int
    
    boolean result = fileUploadService.incrementUploadedChunks(1L);
    
    assertTrue(result);
    assertEquals(6, mockFile.getUploadedChunks());
    verify(fileUploadMapper).updateById(mockFile);
}
}