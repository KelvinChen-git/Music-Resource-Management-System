import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Files;
import java.nio.file.Path;
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
    private com.taffy.music.service.UploadAccessService uploadAccessService;

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

    @TempDir
    Path tempDirectory;

    @BeforeAll
    static void initializeMybatisMetadata() {
        TableInfoHelper.initTableInfo(
            new MapperBuilderAssistant(new MybatisConfiguration(), ""), MusicResources.class);
    }

    @BeforeEach
    void setUp() {
        // 手动注入 baseMapper
        ReflectionTestUtils.setField(musicService, "baseMapper", musicResourceMapper);
        
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
        ReflectionTestUtils.setField(musicService, "uploadPath", tempDirectory.toString());
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
        when(uploadAccessService.requireOwnedLocked(1L)).thenReturn(testFileUpload);

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
        RecycleBinSettings settings = new RecycleBinSettings();
        settings.setDefaultRetentionDays(14);
        when(recycleBinSettingsService.getSettings()).thenReturn(settings);
        when(musicResourceMapper.updateById(any(MusicResources.class))).thenReturn(1);
        when(recycleBinService.moveToRecycleBin(any(), anyString())).thenReturn(true);

        try (MockedStatic<UserContext> userContext = mockStatic(UserContext.class)) {
            userContext.when(UserContext::getCurrentUserId).thenReturn(testUserId);

            // Act
            boolean result = musicService.moveToRecycleBin(1L, "test");

            // Assert
            assertTrue(result);
            assertTrue(testMusic.getIsDeleted());
            assertEquals(14, testMusic.getRetentionPeriod());
            assertEquals(testMusic.getDeletedAt().plusDays(14), testMusic.getPermanentDeleteTime());
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

        when(musicResourceMapper.deleteById(1L)).thenReturn(1);

        // Act
        boolean result = musicService.deleteMusicResourceConditionally(1L, "test");

        // Assert
        assertTrue(result);
        verify(musicResourceMapper).deleteById(1L);
    }
    @Test
    void parseAndSaveMetadata_ShouldHandleMP3File() throws Exception {
        // Forty complete MPEG-1 Layer III frames, rather than a truncated header.
        byte[] frame = new byte[417];
        frame[0] = (byte) 0xff;
        frame[1] = (byte) 0xfb;
        frame[2] = (byte) 0x90;
        Path mp3 = tempDirectory.resolve("synthetic.mp3");
        try (var output = Files.newOutputStream(mp3)) {
            for (int i = 0; i < 40; i++) output.write(frame);
        }
        testFileUpload.setFilePath(mp3.getFileName().toString());
        testFileUpload.setFileSize(Files.size(mp3));
        when(uploadAccessService.requireOwnedLocked(1L)).thenReturn(testFileUpload);
        MusicCategory category = new MusicCategory();
        category.setCategoryId(1);
        when(musicCategoryService.getById(1)).thenReturn(category);
        when(musicResourceMapper.insert(any(MusicResources.class))).thenAnswer(invocation -> {
            MusicResources entity = invocation.getArgument(0);
            entity.setMusicid(999L);
            return 1;
        });
        try (MockedStatic<UserContext> context = mockStatic(UserContext.class)) {
            context.when(UserContext::getCurrentUserId).thenReturn(testUserId);
            MusicMetadataVO input = new MusicMetadataVO();
            input.setTitle("Test Title");
            input.setArtist("Test Artist");
            input.setCategoryId(1);
            MusicMetadataVO result = musicService.parseAndSaveMetadata(1L, input);
            assertEquals("Test Title", result.getTitle());
            assertEquals("Test Artist", result.getArtist());
            ArgumentCaptor<MusicResources> inserted = ArgumentCaptor.forClass(MusicResources.class);
            verify(musicResourceMapper).insert(inserted.capture());
            assertEquals(testUserId, inserted.getValue().getUserid());
            assertEquals("pending", inserted.getValue().getApprovalStatus());
            assertEquals("synthetic.mp3", inserted.getValue().getFilePath());
        }
    }
}