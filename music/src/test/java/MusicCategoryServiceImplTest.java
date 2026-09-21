import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfo;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.domain.MusicCategory;
import com.taffy.music.mapper.MusicCategoryMapper;
import com.taffy.music.service.impl.MusicCategoryServiceImpl;

import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MusicCategoryServiceImplTest {

    @Mock
    private MusicCategoryMapper musicCategoryMapper;

    @Spy
    private MusicCategoryServiceImpl musicCategoryService;

    private MusicCategory testCategory;

    @BeforeEach
    void setUp() {
        // 初始化测试数据
        testCategory = new MusicCategory();
        testCategory.setCategoryId(1);
        testCategory.setCategoryName("Test Category");
        testCategory.setDescription("Test Description");
        musicCategoryService = new MusicCategoryServiceImpl();
    
         MybatisConfiguration configuration = new MybatisConfiguration();
    configuration.setMapUnderscoreToCamelCase(true); // 开启驼峰映射
    TableInfoHelper.initTableInfo(
        new MapperBuilderAssistant(configuration, ""), // 初始化元数据
        MusicCategory.class
    );
        // 使用反射注入mapper
        try {
            Field baseMapperField = ServiceImpl.class.getDeclaredField("baseMapper");
            baseMapperField.setAccessible(true);
            baseMapperField.set(musicCategoryService, musicCategoryMapper);
        } catch (Exception e) {
            throw new RuntimeException("Failed to inject mapper", e);
        }
    }

    @Test
    void getCategories_ShouldReturnPage() {
        // Arrange
        Page<MusicCategory> expectedPage = new Page<>(1, 10);
        expectedPage.setRecords(Collections.singletonList(testCategory));
        
        // 解决方案1：最简单的通用方案
        doReturn(expectedPage).when(musicCategoryMapper).selectPage(any(Page.class), any());

        // Act
        Page<MusicCategory> result = musicCategoryService.getCategories(1, 10);

        // Assert
        assertNotNull(result);
        assertEquals(1, result.getRecords().size());
        verify(musicCategoryMapper).selectPage(any(Page.class), any());
    }
//
@Test
void getCategoryByName_ShouldReturnCategory_WhenExists() {
    // 1. 准备测试数据
    MusicCategory expected = new MusicCategory();
    expected.setCategoryId(1);
    expected.setCategoryName("Test Category");

    // 2. 精确mock（匹配实际调用方式）
    doReturn(expected).when(musicCategoryMapper).selectOne(
        argThat(wrapper -> {
            // 可以添加对wrapper的更多断言
            return wrapper instanceof LambdaQueryWrapper;
        }),
        eq(true)  // MyBatis-Plus总是传true
    );

    // 3. 执行测试
    MusicCategory result = musicCategoryService.getCategoryByName("Test Category");

    // 4. 验证结果
    assertNotNull(result);
    assertEquals(1, result.getCategoryId());
    assertEquals("Test Category", result.getCategoryName());
    
    // 5. 验证调用方式
    verify(musicCategoryMapper).selectOne(
        argThat(wrapper -> wrapper != null),
        eq(true)
    );
}
//
@Test
void getCategoryByName_ShouldReturnNull_WhenNotExists() {
    // 1. 准备 - 模拟返回null
    doReturn(null).when(musicCategoryMapper).selectOne(
        argThat(wrapper -> wrapper != null),  // 确保wrapper不为null
        eq(true)  // MyBatis-Plus总是传true
    );

    // 2. 执行
    MusicCategory result = musicCategoryService.getCategoryByName("Nonexistent");

    // 3. 验证
    assertNull(result);
    
    // 4. 验证调用参数
    verify(musicCategoryMapper).selectOne(
        argThat(wrapper -> {
            // 可以添加对wrapper的更多断言
            return wrapper instanceof LambdaQueryWrapper;
        }),
        eq(true)
    );
}
//
@Test
void createCategory_ShouldSuccess_WhenNameNotExists() {
    // Arrange
    // 1. 模拟名称检查返回null（名称不存在）
    doReturn(null).when(musicCategoryMapper).selectOne(
        any(LambdaQueryWrapper.class),
        anyBoolean()
    );
    
    // 2. 模拟插入成功
    doReturn(1).when(musicCategoryMapper).insert(any(MusicCategory.class));

    // Act
    MusicCategory result = musicCategoryService.createCategory(testCategory);

    // Assert
    assertNotNull(result);
    assertEquals("Test Category", result.getCategoryName());
    
    // 验证交互
    verify(musicCategoryMapper, times(1)).selectOne(any(), anyBoolean()); // 只应调用1次
    verify(musicCategoryMapper).insert(testCategory);
}
    @Test
    void createCategory_ShouldThrow_WhenNameExists() {
        // Arrange
        doReturn(testCategory).when(musicCategoryMapper).selectOne(
            any(LambdaQueryWrapper.class)
        );

        // Act & Assert
        assertThrows(RuntimeException.class, () -> {
            musicCategoryService.createCategory(testCategory);
        });
    }
//
    @Test
    void updateCategory_ShouldSuccess_WhenValidInput() {
        // Arrange
        MusicCategory existing = new MusicCategory();
        existing.setCategoryId(1);
        existing.setCategoryName("Old Name");
        
        MusicCategory updateData = new MusicCategory();
        updateData.setCategoryName("New Name");
        updateData.setDescription("New Description");
    
        doReturn(existing).when(musicCategoryMapper).selectById(1);
        // 修复点：匹配两个参数（LambdaQueryWrapper 和 boolean）
        doReturn(null).when(musicCategoryMapper).selectOne(any(LambdaQueryWrapper.class), anyBoolean());
        doReturn(1).when(musicCategoryMapper).updateById(any(MusicCategory.class));
    
        // Act
        MusicCategory result = musicCategoryService.updateCategory(1, updateData);
    
        // Assert
        assertNotNull(result);
        assertEquals("New Name", result.getCategoryName());
        assertEquals("New Description", result.getDescription());
    }

    @Test
    void updateCategory_ShouldThrow_WhenCategoryNotExists() {
        // Arrange
        doReturn(null).when(musicCategoryMapper).selectById(1);

        // Act & Assert
        assertThrows(RuntimeException.class, () -> {
            musicCategoryService.updateCategory(1, testCategory);
        });
    }

    @Test
    void updateCategory_ShouldThrow_WhenNameConflict() {
        // Arrange
        MusicCategory existing = new MusicCategory();
        existing.setCategoryId(1);
        existing.setCategoryName("Old Name");
        
        MusicCategory anotherCategory = new MusicCategory();
        anotherCategory.setCategoryId(2);
        anotherCategory.setCategoryName("New Name");

        doReturn(existing).when(musicCategoryMapper).selectById(1);
        doReturn(anotherCategory).when(musicCategoryMapper).selectOne(any(LambdaQueryWrapper.class));

        // Act & Assert
        assertThrows(RuntimeException.class, () -> {
            musicCategoryService.updateCategory(1, anotherCategory);
        });
    }
//


    @Test
    void deleteCategory_ShouldThrow_WhenCategoryNotExists() {
        // Arrange
        doReturn(null).when(musicCategoryMapper).selectById(1);

        // Act & Assert
        assertThrows(RuntimeException.class, () -> {
            musicCategoryService.deleteCategory(1);
        });
        
        // 使用anyInt()解决歧义
        verify(musicCategoryMapper, never()).deleteById(anyInt());
    }
    @Test
void deleteCategory_ShouldSuccess_WhenCategoryExists() {
    // Arrange
    // 1. 模拟记录存在
    when(musicCategoryMapper.selectById(1)).thenReturn(testCategory);
    
    // 2. 直接返回删除成功，绕过 TableInfo 检查
    when(musicCategoryMapper.deleteById(1)).thenReturn(1); // 关键修改

    // Act
    musicCategoryService.deleteCategory(1);

    // Assert
    verify(musicCategoryMapper).selectById(1);
    verify(musicCategoryMapper).deleteById(1);
}
}