import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.domain.*;
import com.taffy.music.mapper.MusicResourceMapper;
import com.taffy.music.service.*;
import com.taffy.music.service.impl.MusicResourceServiceImpl;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.MusicMetadataVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.File;
import java.io.FileOutputStream;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MusicResourceServiceImplTest {

    @Mock
    private MusicResourceMapper musicResourceMapper;

    @Mock
    private MusicCategoryService musicCategoryService;

    @Mock
    private FileUploadService fileUploadService;

    @Mock
    private UserService userService;

    @Mock
    private RecycleBinService recycleBinService;

    @Mock
    private RecycleBinSettingsService recycleBinSettingsService;

    @Mock
    private MusicTagService musicTagService;

    @InjectMocks
    private MusicResourceServiceImpl musicService;

    private MusicResources testMusic;
    private FileUpload testFileUpload;
    private final Long testUserId = 100L;
    private static final Logger log = LoggerFactory.getLogger(MusicResourceServiceImplTest.class);

    @BeforeEach
    void setUp() {
        // 手动注入 baseMapper
        ReflectionTestUtils.setField(musicService, "baseMapper", musicResourceMapper);
        
        // 其他初始化...
        testMusic = new MusicResources();
        testMusic.setMusicid(1L);
        testMusic.setCategoryid(1L); // 新增此行
        // 初始化测试音乐资源
        testMusic = new MusicResources();
        testMusic.setMusicid(1L);
        testMusic.setTitle("Test Song");
        testMusic.setArtist("Test Artist");
        testMusic.setApprovalStatus("pending");
        testMusic.setIsDeleted(false);

        // 初始化测试文件上传记录
        testFileUpload = new FileUpload();
        testFileUpload.setId(1L);
        testFileUpload.setFilePath("test.mp3");
        testFileUpload.setFileType("mp3");
        testFileUpload.setStatus(1);

        // 设置上传路径
        ReflectionTestUtils.setField(musicService, "uploadPath", "src/test/resources");
    }

    /* 核心功能测试 */
    
    @Test
    void getMusicResourceList_ShouldReturnFilteredResults() {
        // Arrange
        Page<MusicResources> page = new Page<>(1, 10);
        when(musicResourceMapper.selectMusicPageWithComplexFilters(any(), anyMap()))
            .thenReturn(page);

        // Act
        Page<MusicResources> result = musicService.getMusicResourceList(
            "test", "artist", "album", 1, true, 1, 10, 
            100L, 200L, "approved", "title", "asc", 
            List.of(1L,2L), LocalDate.now().toString(), LocalDate.now().toString(), "keyword");

        // Assert
        assertNotNull(result);
        verify(musicResourceMapper).selectMusicPageWithComplexFilters(any(), anyMap());
    }
//
@Test
void getMusicResourceById_ShouldReturnMusicWithCategory() {
    // Arrange
    // 确保 testMusic 有 categoryid
    testMusic.setCategoryid(1L);

    // 模拟分类服务返回带名称的分类
    MusicCategory mockCategory = new MusicCategory();
    mockCategory.setCategoryName("Test Category"); // 设置分类名称
    
    when(musicResourceMapper.selectById(1)).thenReturn(testMusic);
    when(musicCategoryService.getById(1L)).thenReturn(mockCategory); // 使用具体ID匹配

    // Act
    MusicResources result = musicService.getMusicResourceById(1);

    // Assert
    assertNotNull(result);
    assertEquals("Test Category", result.getCategoryName()); // 更严格的断言
}

    @Test
    void updateMusicResource_ShouldUpdateMetadataAndTags() {
        // Arrange
        MusicMetadataVO metadata = new MusicMetadataVO();
        metadata.setTitle("New Title");
        metadata.setTagIds(List.of(1L,2L));
        
        when(musicResourceMapper.selectById(1L)).thenReturn(testMusic);
        when(musicResourceMapper.updateById(any())).thenReturn(1);

        try (MockedStatic<UserContext> userContext = mockStatic(UserContext.class)) {
            userContext.when(UserContext::getCurrentUserId).thenReturn(testUserId);

            // Act
            boolean result = musicService.updateMusicResource(1L, metadata);

            // Assert
            assertTrue(result);
            verify(musicTagService).listByIds(anyList());
        }
    }



    @Test
    void parseAndSaveMetadata_ShouldRejectNonMP3File() {
        // Arrange
        testFileUpload.setFileType("wav");
        when(fileUploadService.getById(1L)).thenReturn(testFileUpload);

        // Act & Assert
        assertThrows(RuntimeException.class, 
            () -> musicService.parseAndSaveMetadata(1L, new MusicMetadataVO()));
    }

    /* 审批流程测试 */
    
    @Test
    void approveMusicResource_ShouldRequireAdmin() {
        // Arrange
        when(musicResourceMapper.selectById(1)).thenReturn(testMusic);
        when(userService.isAdmin(testUserId)).thenReturn(false);

        try (MockedStatic<UserContext> userContext = mockStatic(UserContext.class)) {
            userContext.when(UserContext::getCurrentUserId).thenReturn(testUserId);

            // Act & Assert
            assertThrows(RuntimeException.class, 
                () -> musicService.approveMusicResource(1));
        }
    }

    /* 回收站测试 */
    
    @Test
    void moveToRecycleBin_ShouldUpdateDeleteStatus() {
        // Arrange
        when(musicResourceMapper.selectById(1L)).thenReturn(testMusic);
        when(recycleBinService.moveToRecycleBin(any(), anyString())).thenReturn(true);

        try (MockedStatic<UserContext> userContext = mockStatic(UserContext.class)) {
            userContext.when(UserContext::getCurrentUserId).thenReturn(testUserId);

            // Act
            boolean result = musicService.moveToRecycleBin(1L, "test");

            // Assert
            assertTrue(result);
            assertTrue(testMusic.getIsDeleted());
        }
    }

    @Test
    void restoreFromRecycleBin_ShouldRecoverResource() {
        // Arrange
        testMusic.setIsDeleted(true);
        when(musicResourceMapper.selectById(1L)).thenReturn(testMusic);
        when(musicResourceMapper.updateById(any())).thenReturn(1);

        // Act
        boolean result = musicService.restoreFromRecycleBin(1L);

        // Assert
        assertTrue(result);
        assertFalse(testMusic.getIsDeleted());
    }

    /* 标签管理测试 */
    
    @Test
    void updateMusicTags_ShouldValidateTagOwnership() {
        // Arrange
        MusicTags validTag = new MusicTags();
        validTag.setTagId(1L);
        validTag.setUserId(testUserId);
        
        MusicTags invalidTag = new MusicTags();
        invalidTag.setTagId(2L);
        invalidTag.setUserId(999L);

        when(musicTagService.listByIds(any())).thenReturn(Arrays.asList(validTag, invalidTag));

        // Act
        musicService.updateMusicTags(1L, testUserId, List.of(1L,2L));

        // Assert
        verify(musicResourceMapper).insertMusicTag(eq(1L), eq(1L));
        verify(musicResourceMapper, never()).insertMusicTag(eq(1L), eq(2L));
    }

    /* 播放计数测试 */
    
    @Test
    void incrementPlayCount_ShouldUpdateDatabase() {
        // Act
        musicService.incrementPlayCount(1L);

        // Assert
        verify(musicResourceMapper).update(any(), any());
    }

    /* 条件删除测试 */
    
    @Test
    void deleteMusicResourceConditionally_ShouldCheckFileExistence() {
        // Arrange
        testMusic.setFilePath("nonexistent.mp3");
        when(musicResourceMapper.selectById(1L)).thenReturn(testMusic);

        // Act
        boolean result = musicService.deleteMusicResourceConditionally(1L, "test");

        // Assert
        assertTrue(result);
        verify(musicResourceMapper).deleteById(1L);
    }
    @Test
    void parseAndSaveMetadata_ShouldHandleMP3File() throws Exception {
        // ============== 1. 创建临时MP3文件 ==============
        File mp3File = File.createTempFile("test", ".mp3");
        try (FileOutputStream fos = new FileOutputStream(mp3File)) {
            // 写入有效的MP3帧数据（示例）
            byte[] mp3Data = new byte[] {
                // ID3v2 Header (10 bytes)
                (byte)0x49, (byte)0x44, (byte)0x33, (byte)0x03, (byte)0x00,
                (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00, (byte)0x00,
                // MPEG Audio Frame Header (4 bytes)
                (byte)0xFF, (byte)0xFB, (byte)0x50, (byte)0x00
            };
            fos.write(mp3Data);
            log.info("创建临时MP3文件: {}", mp3File.getAbsolutePath());
        }

        // ============== 2. 配置服务路径和模拟对象 ==============
        ReflectionTestUtils.setField(musicService, "uploadPath", mp3File.getParent());

        FileUpload testFileUpload = new FileUpload();
        testFileUpload.setId(1L);
        testFileUpload.setFilePath(mp3File.getName());
        testFileUpload.setFileType("mp3");
        testFileUpload.setStatus(1);
        testFileUpload.setFileSize(mp3File.length());

        // ============== 3. 模拟依赖调用 ==============
        when(fileUploadService.getById(1L)).thenReturn(testFileUpload);
        when(fileUploadService.getByFilePath(anyString())).thenReturn(testFileUpload);

        MusicCategory mockCategory = new MusicCategory();
        mockCategory.setCategoryId(1);
        mockCategory.setCategoryName("TestCategory");
        when(musicCategoryService.getById(1)).thenReturn(mockCategory);

        when(musicResourceMapper.insert(any())).thenAnswer(invocation -> {
            MusicResources entity = invocation.getArgument(0);
            entity.setMusicid(999L); // 模拟生成ID
            return 1;
        });

        // ============== 4. 执行测试逻辑 ==============
        try (MockedStatic<UserContext> userContext = mockStatic(UserContext.class)) {
            userContext.when(UserContext::getCurrentUserId).thenReturn(1001L);
            when(userService.isAdmin(1001L)).thenReturn(false);

            MusicMetadataVO input = new MusicMetadataVO();
            input.setTitle("Test Title");
            input.setArtist("Test Artist");
            input.setCategoryId(1);

            MusicMetadataVO result = musicService.parseAndSaveMetadata(1L, input);

            // ============== 5. 验证结果 ==============
            assertNotNull(result, "返回的元数据不应为空");
            assertEquals("Test Title", result.getTitle(), "标题应正确解析");
            assertEquals("Test Artist", result.getArtist(), "艺术家应正确解析");

            // 验证数据库保存操作
            verify(musicResourceMapper).insert(any(MusicResources.class));
        } finally {
            // ============== 6. 清理临时文件 ==============
            if (mp3File.exists() && !mp3File.delete()) {
                log.warn("未能删除临时文件: {}", mp3File.getAbsolutePath());
            }
        }
    }
}