import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.MusicTags;
import com.taffy.music.mapper.MusicTagMapper;
import com.taffy.music.service.impl.MusicTagServiceImpl;

import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.util.StringUtils;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MusicTagServiceImplTest {

    @Mock
    private MusicTagMapper musicTagMapper;

    

    private MusicTags testTag;
    private final Long testUserId = 1L;
    private final Long testTagId = 100L;
    private final String testTagName = "Test Tag";

    @Spy  // 使用 @Spy 替代 @InjectMocks
    private MusicTagServiceImpl musicTagService;
    @BeforeEach
    void setUp() throws Exception{
        testTag = new MusicTags();
        testTag.setTagId(testTagId);
        testTag.setUserId(testUserId);
        testTag.setTagName(testTagName);
        Field baseMapper = ServiceImpl.class.getDeclaredField("baseMapper");
        baseMapper.setAccessible(true);
        baseMapper.set(musicTagService, musicTagMapper);
    }
    @BeforeAll
    static void init() {
        // 初始化 Lambda 缓存
        TableInfoHelper.initTableInfo(
            new MapperBuilderAssistant(new MybatisConfiguration(), ""),
            MusicTags.class
        );
    }

    @Test
void createUserTag_ShouldThrow_WhenTagNameEmpty() {
    // 这个测试不需要任何 Mock 配置
    assertThrows(IllegalArgumentException.class, () -> {
        musicTagService.createUserTag(testUserId, "");
    });
}

@Test
void createUserTag_ShouldSuccess_WhenInputValid() {
    // 在此测试中配置需要的 Mock
    doReturn(musicTagMapper).when(musicTagService).getBaseMapper();
    when(musicTagService.count(any(LambdaQueryWrapper.class))).thenReturn(0L);
    when(musicTagMapper.insert(any(MusicTags.class))).thenReturn(1);

    MusicTags result = musicTagService.createUserTag(testUserId, "New Tag");
    assertNotNull(result);
}

@Test
void createUserTag_ShouldThrow_WhenTagNameTooLong() {
    // Arrange
    String longName = "a".repeat(51); // Java 11+ 原生方法

    // Act & Assert
    assertThrows(IllegalArgumentException.class, () -> {
        musicTagService.createUserTag(testUserId, longName);
    });
}

@Test
void createUserTag_ShouldThrow_WhenTagExists() {
    // 1. 准备有效测试数据（必须符合校验规则）
    String validTagName = "ExistingTag"; // 长度1-50的非空字符串
    
    // 2. Mock基类方法（关键区别）
    doReturn(1L).when(musicTagService).count(any(LambdaQueryWrapper.class));
    
    // 3. 执行测试
    assertThrows(RuntimeException.class, () -> {
        musicTagService.createUserTag(testUserId, validTagName);
    });
    
    // 4. 验证（验证count方法被调用）
    verify(musicTagService).count(any(LambdaQueryWrapper.class));
}

@Test
    void getTagsByUserId_ShouldReturnPage() {
        // 1. 准备测试数据
        Page<MusicTags> page = new Page<>(1, 10);
        List<MusicTags> mockData = Collections.singletonList(new MusicTags());
        page.setRecords(mockData);
        
        // 2. Mock基类方法（关键区别）
        doReturn(page).when(musicTagService).page(
            eq(page), 
            any(LambdaQueryWrapper.class)
        );
        
        // 3. 执行测试
        Page<MusicTags> result = musicTagService.getTagsByUserId(testUserId, page);
        
        // 4. 断言和验证
        assertNotNull(result);
        assertEquals(1, result.getRecords().size());
        verify(musicTagService).page(eq(page), any(LambdaQueryWrapper.class));
    }

@Test
void getUserTagById_ShouldReturnTag_WhenExists() {
    // Arrange - 匹配两个参数的调用
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class), anyBoolean()))
        .thenReturn(testTag);

    // Act
    MusicTags result = musicTagService.getUserTagById(testTagId, testUserId);

    // Assert
    assertNotNull(result);
    assertEquals(testTagId, result.getTagId());
    assertEquals(testUserId, result.getUserId());
}
//
@Test
void getUserTagById_ShouldThrow_WhenTagNotFound() {
    // Arrange
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

    // Act & Assert
    assertThrows(RuntimeException.class, () -> {
        musicTagService.getUserTagById(testTagId, testUserId);
    });
}

@Test
void updateUserTag_ShouldUpdate_WhenNameChanged() {
    // Arrange
    String newName = "Updated Tag";
    MusicTags existingTag = new MusicTags();
    existingTag.setTagId(testTagId);
    existingTag.setUserId(testUserId);
    existingTag.setTagName("Old Tag");
    
    // 修正：匹配两个参数
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class), anyBoolean()))
        .thenReturn(existingTag);
    when(musicTagMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
    when(musicTagMapper.updateById(any(MusicTags.class))).thenReturn(1);

    // Act
    MusicTags result = musicTagService.updateUserTag(testTagId, testUserId, newName);

    // Assert
    assertEquals(newName, result.getTagName());
    verify(musicTagMapper).updateById(argThat(tag -> 
        tag.getTagName().equals(newName) &&
        tag.getTagId().equals(testTagId)
    ));
}
//

@Test
void updateUserTag_ShouldThrow_WhenNameExists() {
    // Arrange
    String existingName = "Existing Tag";
    MusicTags existingTag = new MusicTags();
    existingTag.setTagId(testTagId);
    existingTag.setUserId(testUserId);
    existingTag.setTagName("Old Tag");
    
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingTag);
    when(musicTagMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

    // Act & Assert
    assertThrows(RuntimeException.class, () -> {
        musicTagService.updateUserTag(testTagId, testUserId, existingName);
    });
}
//
@Test
void updateUserTag_ShouldNotUpdate_WhenNameSame() {
    // Arrange
    String sameName = "SameTag";
    MusicTags existingTag = new MusicTags();
    existingTag.setTagId(testTagId);
    existingTag.setUserId(testUserId);
    existingTag.setTagName(sameName);
    
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class), eq(true)))
        .thenReturn(existingTag);

    // Act
    MusicTags result = musicTagService.updateUserTag(testTagId, testUserId, sameName);

    // Assert
    assertEquals(sameName, result.getTagName());
    verify(musicTagMapper, never()).updateById(any(MusicTags.class));
    
    // 简化验证 - 只验证方法调用
    verify(musicTagMapper).selectOne(any(LambdaQueryWrapper.class), eq(true));
}


@Test
void deleteUserTag_ShouldThrow_WhenTagNotFound() {
    // Arrange
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

    // Act & Assert
    assertThrows(RuntimeException.class, () -> {
        musicTagService.deleteUserTag(testTagId, testUserId);
    });
}
@Test
void deleteUserTag_ShouldSuccess_WhenTagExists() {
    // Arrange - 匹配两个参数
    when(musicTagMapper.selectOne(any(LambdaQueryWrapper.class), eq(true)))
        .thenReturn(testTag);
    when(musicTagMapper.deleteById(testTagId)).thenReturn(1);

    // Act
    musicTagService.deleteUserTag(testTagId, testUserId);

    // Assert
    verify(musicTagMapper).selectOne(any(LambdaQueryWrapper.class), eq(true));
    verify(musicTagMapper).deleteById(testTagId);
}
}