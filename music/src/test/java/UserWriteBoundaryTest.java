import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.taffy.music.domain.Users;
import com.taffy.music.dto.ChangePasswordDTO;
import com.taffy.music.dto.ResetPasswordDTO;
import com.taffy.music.mapper.UserMapper;
import com.taffy.music.service.impl.UserServiceImpl;
import com.taffy.music.utils.PasswordEncoder;
import com.taffy.music.utils.UserContext;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.test.util.ReflectionTestUtils;
import java.time.LocalDateTime;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class UserWriteBoundaryTest {
    @BeforeAll static void metadata() {
        TableInfoHelper.initTableInfo(new MapperBuilderAssistant(new MybatisConfiguration(), "user-writes"), Users.class);
    }

    @ParameterizedTest
    @ValueSource(strings={"lock", "unlock", "lockReason", "changePassword", "adminReset", "codeReset"})
    void writesOnlyOperationColumnsFromStaleSnapshot(String operation) {
        var mapper=mock(UserMapper.class);
        var encoder=mock(PasswordEncoder.class);
        var cache=mock(Cache.class);
        var caches=mock(CacheManager.class);
        var service=new UserServiceImpl();
        ReflectionTestUtils.setField(service,"userMapper",mapper);
        ReflectionTestUtils.setField(service,"baseMapper",mapper);
        ReflectionTestUtils.setField(service,"passwordEncoder",encoder);
        ReflectionTestUtils.setField(service,"cacheManager",caches);
        var snapshot=new Users();snapshot.setUserid(41L);snapshot.setAvatar("old.png");
        snapshot.setEmail("old@example.invalid");snapshot.setName("old");snapshot.setRole("USER");
        snapshot.setPassword("old-hash");snapshot.setIsLocked(false);snapshot.setLockReason("old reason");
        snapshot.setUnlockTime(LocalDateTime.of(2020,1,1,0,0));
        // Values another writer has already committed after this snapshot was read.
        Map<String,Object> stored=new HashMap<>(Map.of("avatar","new.png","email","new@example.invalid",
                "name","new","role","ADMIN","password","concurrent-hash","is_locked",true,
                "lock_reason","concurrent reason","unlock_time",LocalDateTime.of(2025,1,1,0,0)));
        Map<String,Object> concurrent=new HashMap<>(stored);
        Set<String> expected=new HashSet<>(Set.of("updated_at"));
        switch(operation) {
            case "lock" -> expected.addAll(Set.of("is_locked","lock_time","unlock_time"));
            case "lockReason" -> expected.addAll(Set.of("is_locked","lock_time","unlock_time","lock_reason"));
            case "unlock" -> expected.addAll(Set.of("is_locked","unlock_time"));
            default -> expected.add("password");
        }
        if(operation.equals("codeReset")) {
            when(mapper.selectOne(any(Wrapper.class))).thenReturn(snapshot);
            when(caches.getCache("passwordResetCodes")).thenReturn(cache);
            when(cache.get("old@example.invalid",String.class)).thenReturn("123456");
        } else when(mapper.selectById(41L)).thenReturn(snapshot);
        if(operation.contains("Password")||operation.endsWith("Reset")) when(encoder.encode("new-secret")).thenReturn("new-hash");
        if(operation.equals("changePassword")) when(encoder.matches("old-secret","old-hash")).thenReturn(true);
        when(mapper.update(isNull(),any(Wrapper.class))).thenAnswer(invocation -> {
            var changes=(LambdaUpdateWrapper<Users>)invocation.getArgument(1);
            assertTrue(changes.getSqlSegment().contains("userid"));
            assertTrue(changes.getParamNameValuePairs().containsValue(41L));
            Set<String> columns=new HashSet<>();
            var assignments=java.util.regex.Pattern.compile("([a-z_]+)=#\\{ew\\.paramNameValuePairs\\.([^}]+)}")
                    .matcher(changes.getSqlSet());
            while(assignments.find()) {
                String column=assignments.group(1);columns.add(column);
                stored.put(column,changes.getParamNameValuePairs().get(assignments.group(2)));
            }
            assertEquals(expected,columns,changes.getSqlSet());return 1;
        });
        try(var context=mockStatic(UserContext.class)) {
            context.when(UserContext::getCurrentUserId).thenReturn(41L);
            switch(operation) {
                case "lock" -> service.lockUser(41L);
                case "unlock" -> service.unlockUser(41L);
                case "lockReason" -> service.lockUserWithReason(41L,"requested reason");
                case "adminReset" -> assertTrue(service.resetUserPassword(41L,"new-secret"));
                case "changePassword" -> {
                    var dto=new ChangePasswordDTO();dto.setOldPassword("old-secret");
                    dto.setNewPassword("new-secret");dto.setConfirmPassword("new-secret");
                    assertTrue(service.changePassword(dto));
                }
                case "codeReset" -> {
                    var dto=new ResetPasswordDTO();dto.setEmail("old@example.invalid");dto.setCode("123456");
                    dto.setNewPassword("new-secret");dto.setConfirmPassword("new-secret");
                    assertTrue(service.resetPassword(dto));verify(cache).evict("old@example.invalid");
                }
            }
        }
        verify(mapper).update(isNull(),any(Wrapper.class));
        verify(mapper,never()).updateById(any(Users.class));
        concurrent.forEach((column,value)-> { if(!expected.contains(column)) assertEquals(value,stored.get(column),column); });
        if(expected.contains("password")) assertEquals("new-hash",stored.get("password"));
        else {
            assertEquals(!operation.equals("unlock"),stored.get("is_locked"));
            if(!operation.equals("unlock")) assertNull(stored.get("unlock_time"));
            if(operation.equals("lockReason")) assertEquals("requested reason",stored.get("lock_reason"));
        }
    }
}
