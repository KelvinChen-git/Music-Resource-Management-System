import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.dto.ChangePasswordDTO;
import com.taffy.music.dto.LoginDTO;
import com.taffy.music.dto.RegisterDTO;
import com.taffy.music.dto.UpdateUserInfoDTO;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.UserMapper;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.RecycleBinService;
import com.taffy.music.service.impl.UserServiceImpl;
import com.taffy.music.utils.JwtUtil;
import com.taffy.music.utils.PasswordEncoder;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.UserVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.beans.BeanUtils;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private PasswordEncoder passwordEncoder;
    @Mock
    private JwtUtil jwtUtil;
    @Mock
    private MusicResourceService musicResourceService; 
    @Mock
    private RecycleBinService recycleBinService; // Mock RecycleBinService

    @InjectMocks
    private UserServiceImpl userService;
    

    private Users testUser;

    @BeforeEach
    void setUp() {
        testUser = new Users();
        testUser.setUserid(1L);
        testUser.setEmail("test@example.com");
        testUser.setPassword("encodedPassword");
        testUser.setName("testuser");
        testUser.setIsLocked(false);
        testUser.setCreatedAt(LocalDateTime.now());

        ReflectionTestUtils.setField(userService, "baseMapper", userMapper);
    }

    @Test
    void register_ShouldCreateNewUser_WhenEmailNotExists() {
        RegisterDTO registerDTO = new RegisterDTO();
        registerDTO.setEmail("new@example.com");
        registerDTO.setPassword("password123");
        registerDTO.setName("newuser");

        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
        when(passwordEncoder.encode(anyString())).thenReturn("encodedPassword");
        when(userMapper.insert(any(Users.class))).thenReturn(1);

        UserVO result = userService.register(registerDTO);

        assertNotNull(result);
        assertEquals("newuser", result.getName());
        verify(userMapper, times(1)).insert(any(Users.class));
    }

    @Test
    void register_ShouldThrow_WhenEmailExists() {
        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(testUser);

        RegisterDTO registerDTO = new RegisterDTO();
        registerDTO.setEmail("test@example.com");
        registerDTO.setPassword("password123");
        registerDTO.setName("newuser");

        assertThrows(RuntimeException.class, () -> userService.register(registerDTO));
    }

@Test
void login_ShouldReturnToken_WhenCredentialsCorrect() {
    LoginDTO loginDTO = new LoginDTO();
    loginDTO.setEmail("test@example.com");
    loginDTO.setPassword("password123");

    // 模拟返回的用户
    when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(testUser);
    
    // 模拟密码匹配
    when(passwordEncoder.matches(loginDTO.getPassword(), testUser.getPassword())).thenReturn(true);
    
    // 模拟生成的 token
    when(jwtUtil.generateToken(testUser.getUserid(), testUser.getEmail())).thenReturn("mockedToken");

    // 调用登录方法
    String token = userService.login(loginDTO);

    // 断言
    assertNotNull(token);
    assertEquals("mockedToken", token); // 验证返回的 token
    verify(passwordEncoder, times(1)).matches(loginDTO.getPassword(), testUser.getPassword());
}

    @Test
    void login_ShouldThrow_WhenUserNotFound() {
        LoginDTO loginDTO = new LoginDTO();
        loginDTO.setEmail("notfound@example.com");
        loginDTO.setPassword("password123");

        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

        assertThrows(RuntimeException.class, () -> userService.login(loginDTO));
    }

@Test
void changePassword_ShouldUpdatePassword_WhenOldPasswordCorrect() {
    ChangePasswordDTO changePasswordDTO = new ChangePasswordDTO();
    changePasswordDTO.setOldPassword("oldPassword");
    changePasswordDTO.setNewPassword("newPassword");
    changePasswordDTO.setConfirmPassword("newPassword");

    // 使用 MockedStatic 模拟 UserContext
    try (MockedStatic<UserContext> mocked = Mockito.mockStatic(UserContext.class)) {
        mocked.when(UserContext::getCurrentUserId).thenReturn(1L);
        
        // 模拟用户查询
        when(userMapper.selectById(1L)).thenReturn(testUser);
        
        // 模拟密码匹配
        when(passwordEncoder.matches("oldPassword", testUser.getPassword())).thenReturn(true);
        
        // 模拟密码加密
        when(passwordEncoder.encode("newPassword")).thenReturn("encodedNewPassword");
        
        // 模拟用户更新
        when(userMapper.updateById(any(Users.class))).thenReturn(1);

        // 调用方法
        boolean result = userService.changePassword(changePasswordDTO);

        // 断言
        assertTrue(result);
        assertEquals("encodedNewPassword", testUser.getPassword());
    }
}

@Test
void changePassword_ShouldThrow_WhenOldPasswordIncorrect() {
    ChangePasswordDTO changePasswordDTO = new ChangePasswordDTO();
    changePasswordDTO.setOldPassword("wrongPassword");
    changePasswordDTO.setNewPassword("newPassword");
    changePasswordDTO.setConfirmPassword("newPassword");

    // 使用 MockedStatic 模拟 UserContext
    try (MockedStatic<UserContext> mocked = Mockito.mockStatic(UserContext.class)) {
        mocked.when(UserContext::getCurrentUserId).thenReturn(1L);
        
        // 模拟用户查询
        when(userMapper.selectById(1L)).thenReturn(testUser);
        
        // 模拟密码匹配
        when(passwordEncoder.matches("wrongPassword", testUser.getPassword())).thenReturn(false);

        // 断言
        assertThrows(RuntimeException.class, () -> userService.changePassword(changePasswordDTO));
    }
}

@Test
void getCurrentUserInfo_ShouldReturnUserInfo_WhenLoggedIn() {
    // 使用 MockedStatic 模拟 UserContext
    try (MockedStatic<UserContext> mocked = Mockito.mockStatic(UserContext.class)) {
        mocked.when(UserContext::getCurrentUserId).thenReturn(1L);
        
        // 模拟用户查询
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // 调用方法
        UserVO result = userService.getCurrentUserInfo();

        // 断言
        assertNotNull(result);
        assertEquals("testuser", result.getName());
    }
}

    @Test
    void getCurrentUserInfo_ShouldThrow_WhenNotLoggedIn() {
        when(UserContext.getCurrentUserId()).thenReturn(null);

        assertThrows(RuntimeException.class, () -> userService.getCurrentUserInfo());
    }

@Test
void updateCurrentUserInfo_ShouldUpdateUserInfo() {
    UpdateUserInfoDTO updateUserInfoDTO = new UpdateUserInfoDTO();
    updateUserInfoDTO.setName("updateduser");
    updateUserInfoDTO.setAvatar("newAvatar.png");

    // 使用 MockedStatic 模拟 UserContext
    try (MockedStatic<UserContext> mocked = Mockito.mockStatic(UserContext.class)) {
        mocked.when(UserContext::getCurrentUserId).thenReturn(1L);
        
        // 模拟用户查询
        when(userMapper.selectById(1L)).thenReturn(testUser);
        
        // 模拟用户更新
        when(userMapper.updateById(any(Users.class))).thenReturn(1);

        // 调用方法
        UserVO result = userService.updateCurrentUserInfo(updateUserInfoDTO);

        // 更新 testUser 的属性
        testUser.setName(updateUserInfoDTO.getName());
        testUser.setAvatar(updateUserInfoDTO.getAvatar());

        // 断言
        assertEquals("updateduser", testUser.getName());
        assertEquals("newAvatar.png", testUser.getAvatar());
    }
}

    @Test
    void deleteUser_ShouldThrow_WhenUserNotFound() {
        when(userMapper.selectById(1L)).thenReturn(null);

        assertThrows(RuntimeException.class, () -> userService.deleteUser(1L));
    }

    @Test
    void lockUser_ShouldLockUser_WhenUserExists() {
        when(userMapper.selectById(1L)).thenReturn(testUser);

        userService.lockUser(1L);

        assertTrue(testUser.getIsLocked());
        verify(userMapper, times(1)).updateById(testUser);
    }

    @Test
    void unlockUser_ShouldUnlockUser_WhenUserExists() {
        testUser.setIsLocked(true);
        when(userMapper.selectById(1L)).thenReturn(testUser);

        userService.unlockUser(1L);

        assertFalse(testUser.getIsLocked());
        verify(userMapper, times(1)).updateById(testUser);
    }

    @Test
    void isAdmin_ShouldReturnTrue_WhenUserIsAdmin() {
        testUser.setRole("ADMIN");
        when(userMapper.selectById(1L)).thenReturn(testUser);

        boolean result = userService.isAdmin(1L);

        assertTrue(result);
    }

    @Test
    void isAdmin_ShouldReturnFalse_WhenUserIsNotAdmin() {
        testUser.setRole("USER");
        when(userMapper.selectById(1L)).thenReturn(testUser);

        boolean result = userService.isAdmin(1L);

        assertFalse(result);
    }

    @Test
    void getUserByUsername_ShouldReturnUser_WhenUserExists() {
        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(testUser);

        Users result = userService.getUserByUsername("testuser");

        assertNotNull(result);
        assertEquals("testuser", result.getName());
    }

    @Test
    void getUserByUsername_ShouldReturnNull_WhenUserNotExists() {
        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

        Users result = userService.getUserByUsername("nonexistent");

        assertNull(result);
    }
//

    @Test
    void deleteUser_ShouldThrowException_WhenUserDoesNotExist() {
        // 模拟用户查询返回 null
        when(userMapper.selectById(1L)).thenReturn(null);

        // 调用删除方法并验证异常
        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            userService.deleteUser(1L);
        });

        // 验证异常消息
        assertEquals("User not found", exception.getMessage());
    }
}