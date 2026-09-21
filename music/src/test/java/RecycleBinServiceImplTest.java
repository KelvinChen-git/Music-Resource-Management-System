import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.RecycleBinMapper;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.UserService;
import com.taffy.music.service.impl.RecycleBinServiceImpl;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.RecycleBinStatsVO;

import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RecycleBinServiceImplTest {

    @Mock
    private RecycleBinMapper recycleBinMapper;

    @Mock
    private MusicResourceService musicResourceService;

    @Mock
    private UserService userService;

    // 使用 @Spy 代理真实对象
    @Spy
    private RecycleBinServiceImpl recycleBinService;

    private RecycleBin testRecycleBin;
    private MusicResources testMusic;
    private Users testUser;

    @BeforeEach
    void setUp() throws Exception {
        // 初始化测试数据
        testUser = new Users();
        testUser.setUserid(1L); // Users 类的主键字段是 userid
        testUser.setName("testUser");

        testMusic = new MusicResources();
        testMusic.setMusicid(100L);
        testMusic.setTitle("Test Song");

        testRecycleBin = new RecycleBin();
        testRecycleBin.setRecycleid(1L);
        testRecycleBin.setMusicid(testMusic.getMusicid());
        testRecycleBin.setDeletedById(testUser.getUserid()); // 使用正确的 getter

        // 手动注入依赖（因为 @Spy 不会自动注入）
        injectDependencies();
        // 初始化 MyBatis-Plus 元数据
        initTableInfo();
    }

    // 手动注入依赖
    private void injectDependencies() throws Exception {
        // 注入 ServiceImpl 的 baseMapper
        Field baseMapperField = RecycleBinServiceImpl.class.getSuperclass().getDeclaredField("baseMapper");
        baseMapperField.setAccessible(true);
        baseMapperField.set(recycleBinService, recycleBinMapper);

        // 注入其他服务
        setField("musicResourceService", musicResourceService);
        setField("userService", userService);
    }

    // 初始化 MyBatis-Plus 元数据（解决 TableInfo 空指针）
    private void initTableInfo() {
        TableInfoHelper.initTableInfo(
            new MapperBuilderAssistant(
                new com.baomidou.mybatisplus.core.MybatisConfiguration(), 
                ""
            ), 
            RecycleBin.class
        );
    }

    // 反射设置字段值
    private void setField(String fieldName, Object value) throws Exception {
        Field field = RecycleBinServiceImpl.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(recycleBinService, value);
    }

    @AfterEach
    void tearDown() {
        // 清理静态上下文（防止跨测试污染）
        try (MockedStatic<UserContext> ignored = mockStatic(UserContext.class)) {
            UserContext.clear(); // 调用清理方法（假设 UserContext 有 clear() 方法）
        }
    }

    @Test
    @Transactional
    void moveToRecycleBin_ShouldCreateRecord() {
        // 使用 MockedStatic 模拟静态方法
        try (MockedStatic<UserContext> mocked = mockStatic(UserContext.class)) {
            // 1. 模拟获取当前用户ID
            mocked.when(UserContext::getCurrentUserId).thenReturn(1L);

            // 2. 模拟依赖行为
            when(userService.getById(1L)).thenReturn(testUser);
            when(musicResourceService.getById(100L)).thenReturn(testMusic);
            doReturn(1).when(recycleBinMapper).insert(any(RecycleBin.class));

            // 3. 执行操作
            boolean result = recycleBinService.moveToRecycleBin(100L, "测试删除");

            // 4. 验证结果
            assertTrue(result);
            verify(recycleBinMapper).insert(any(RecycleBin.class));
        }
    }
//
@Test
void getRecycleBinList_ShouldReturnPagedResults() {
    // 1. 创建分页参数和模拟结果
    Page<RecycleBin> mockPage = new Page<>(1, 10, 1);
    mockPage.setRecords(Collections.singletonList(testRecycleBin));

    // 2. 精确匹配参数并返回模拟结果
    when(recycleBinMapper.selectPage(
        any(Page.class), 
        any(LambdaQueryWrapper.class)
    )).thenReturn(mockPage);

    // 3. 模拟关联服务调用（使用 lenient 避免严格校验）
    lenient().when(musicResourceService.getById(anyLong())).thenReturn(testMusic);
    lenient().when(userService.getById(anyLong())).thenReturn(testUser);

    // 4. 执行测试
    IPage<RecycleBin> result = recycleBinService.getRecycleBinList(
        "Test", "Artist", 1, 10, 1L
    );

    // 5. 验证结果
    assertNotNull(result, "分页结果不应为 null");
    assertEquals(1, result.getTotal());
    assertEquals(1, result.getRecords().size());
    assertEquals("Test Song", result.getRecords().get(0).getMusic().getTitle());
}
//
    @Test
    void restoreFromRecycleBin_ShouldUpdateStatus() {
        // 模拟数据查询
        when(recycleBinMapper.selectById(1L)).thenReturn(testRecycleBin);
        when(musicResourceService.getById(100L)).thenReturn(testMusic);

        // 拦截更新操作
        doReturn(1).when(recycleBinMapper).updateById(any(RecycleBin.class));
        when(musicResourceService.updateById(any(MusicResources.class))).thenReturn(true);

        // 执行恢复操作
        MusicResources restoredMusic = recycleBinService.restoreFromRecycleBin(1L);

        // 验证结果
        assertNotNull(restoredMusic);
        assertFalse(restoredMusic.getIsDeleted());
        assertTrue(testRecycleBin.getRecoveryStatus());
    }

    @Test
    void deleteFromRecycleBin_ShouldMarkAsDeleted() {
        // 模拟数据查询
        when(recycleBinMapper.selectById(1L)).thenReturn(testRecycleBin);
        // 拦截更新操作
        doReturn(1).when(recycleBinMapper).updateById(any(RecycleBin.class));

        // 执行永久删除
        boolean result = recycleBinService.deleteFromRecycleBin(1L);

        // 验证结果
        assertTrue(result);
        assertTrue(testRecycleBin.getPermanentlyDeleted());
        assertNotNull(testRecycleBin.getPermanentDeleteTime());
    }

    @Test
void emptyRecycleBin_ShouldProcessAllItems() {
    // 创建并初始化 RecycleBin 对象
    RecycleBin item1 = new RecycleBin();
    item1.setRecycleid(1L); // 分步设置属性
    RecycleBin item2 = new RecycleBin();
    item2.setRecycleid(2L);

    // 模拟查询结果
    List<RecycleBin> mockItems = Arrays.asList(item1, item2);
    when(recycleBinMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(mockItems);

    // 拦截单个删除操作
    doReturn(true).when(recycleBinService).deleteFromRecycleBin(anyLong());

    // 执行清空操作
    int count = recycleBinService.emptyRecycleBin();

    // 验证结果
    assertEquals(2, count);
    verify(recycleBinService, times(2)).deleteFromRecycleBin(anyLong());
}

    @Test
    void getExpiredItems_ShouldFilterCorrectly() {
        // 模拟查询结果
        List<RecycleBin> mockItems = Collections.singletonList(testRecycleBin);
        when(recycleBinMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(mockItems);

        // 执行查询
        List<RecycleBin> result = recycleBinService.getExpiredItems(7);

        // 验证结果
        assertEquals(1, result.size());
        assertEquals(1L, result.get(0).getRecycleid());
    }

    @Test
void autoCleanupExpiredItems_ShouldReturnCount() {
    // 创建并初始化对象（关键修改）
    RecycleBin item1 = new RecycleBin();
    item1.setRecycleid(1L); // 分步设置属性
    RecycleBin item2 = new RecycleBin();
    item2.setRecycleid(2L);

    // 模拟数据
    List<RecycleBin> mockItems = Arrays.asList(item1, item2); // ✅ 传递有效对象
    when(recycleBinMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(mockItems);
    doReturn(true).when(recycleBinService).deleteFromRecycleBin(anyLong());

    // 执行自动清理
    int count = recycleBinService.autoCleanupExpiredItems();

    // 验证结果
    assertEquals(2, count);
    verify(recycleBinService, times(2)).deleteFromRecycleBin(anyLong()); // 增加验证调用次数
}

    @Test
    void getRecycleBinStats_ShouldAggregateData() {
        // 模拟统计查询
        when(recycleBinMapper.selectCount(any(LambdaQueryWrapper.class)))
            .thenReturn(10L)  // 总项目数
            .thenReturn(3L)   // 即将过期
            .thenReturn(5L)   // 已恢复
            .thenReturn(2L);  // 永久删除

        // 获取统计数据
        RecycleBinStatsVO stats = recycleBinService.getRecycleBinStats();

        // 验证结果
        assertEquals(10L, stats.getTotalItems());
        assertEquals(3L, stats.getExpiringItems());
        assertEquals(5L, stats.getRecoveredItems());
        assertEquals(2L, stats.getPermanentlyDeletedItems());
    }



    @Test
    void restoreAlreadyRecoveredItem_ShouldThrowException() {
        // 设置已恢复状态
        testRecycleBin.setRecoveryStatus(true);
        when(recycleBinMapper.selectById(1L)).thenReturn(testRecycleBin);

        // 验证异常抛出
        assertThrows(RuntimeException.class, () -> 
            recycleBinService.restoreFromRecycleBin(1L)
        );
    }

    @Test
    void deleteNonExistingItem_ShouldReturnFalse() {
        // 模拟记录不存在
        when(recycleBinMapper.selectById(999L)).thenReturn(null);

        // 执行删除
        boolean result = recycleBinService.deleteFromRecycleBin(999L);

        // 验证结果
        assertFalse(result);
    }
    @Test
void emptyUserRecycleBin_ShouldDeleteUserItems() {
    // 1. 创建测试数据
    RecycleBin item1 = new RecycleBin();
    item1.setRecycleid(1L);
    item1.setDeletedById(1L);

    RecycleBin item2 = new RecycleBin();
    item2.setRecycleid(2L);
    item2.setDeletedById(1L);

    List<RecycleBin> mockItems = Arrays.asList(item1, item2);

    // 2. 捕获查询条件
    ArgumentCaptor<LambdaQueryWrapper<RecycleBin>> queryCaptor = 
        ArgumentCaptor.forClass(LambdaQueryWrapper.class);
    when(recycleBinMapper.selectList(queryCaptor.capture())).thenReturn(mockItems);

    // 3. 模拟删除操作
    doReturn(true).when(recycleBinService).deleteFromRecycleBin(anyLong());

    // 4. 执行清空操作
    int count = recycleBinService.emptyUserRecycleBin(1L);

    // 5. 验证结果
    assertEquals(2, count);

    // 6. 获取查询条件和参数
    LambdaQueryWrapper<RecycleBin> usedWrapper = queryCaptor.getValue();
    Map<String, Object> paramMap = usedWrapper.getParamNameValuePairs();
    String generatedSql = usedWrapper.getSqlSegment();

    // 7. 验证 SQL 结构
    assertTrue(generatedSql.contains("deleted_by = #{ew.paramNameValuePairs."));
    assertTrue(generatedSql.contains("recovery_status = #{ew.paramNameValuePairs."));
    assertTrue(generatedSql.contains("permanently_deleted = #{ew.paramNameValuePairs."));

    // 8. 验证参数值
    assertTrue(paramMap.containsValue(1L));
    assertTrue(paramMap.containsValue(false));
}
}