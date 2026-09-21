package com.taffy.music.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.taffy.music.dto.ChangePasswordDTO;
import com.taffy.music.dto.LoginDTO;
import com.taffy.music.dto.RegisterDTO;
import com.taffy.music.dto.UpdateUserInfoDTO;
import com.taffy.music.dto.ResetPasswordDTO;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.RecycleBin;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.UserMapper;
import com.taffy.music.service.MusicResourceService;
import com.taffy.music.service.RecycleBinService;
import com.taffy.music.service.UserService;
import com.taffy.music.utils.JwtUtil;
import com.taffy.music.utils.PasswordEncoder;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.UserVO;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.mail.MailException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.Random;

@Slf4j
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, Users> implements UserService {
    
    @Autowired
    private JwtUtil jwtUtil;
    
    @Autowired
    private PasswordEncoder passwordEncoder;
    
    @Autowired
    private UserMapper userMapper;
    
    @Autowired
    private MusicResourceService musicResourceService;
    
    @Autowired
    private RecycleBinService recycleBinService;

    @Autowired
    private JavaMailSender mailSender;

    @Autowired
    private CacheManager cacheManager;
    
    @Value("${upload.path}")
    private String uploadPath;

    @Value("${spring.mail.username:}")
    private String mailFromAddress;
    
    @Override
    public Optional<Users> getUserById(Long id) {
        return Optional.ofNullable(userMapper.selectById(id));
    }
    
    @Override
    @Transactional
    public UserVO register(RegisterDTO registerDTO) {
        // 检查邮箱是否已存在
        if (isEmailExists(registerDTO.getEmail())) {
            throw new RuntimeException("Email already registered");
        }
        
        // 创建用户实体
        Users user = new Users();
        BeanUtils.copyProperties(registerDTO, user);
        
        // 加密密码
        user.setPassword(passwordEncoder.encode(registerDTO.getPassword()));
        
        // 设置默认角色
        user.setRole("USER");
        
        // 设置验证状态为已验证(1)
        user.setVerificationStatus(true);
        
        // 设置创建时间
        user.setCreatedAt(LocalDateTime.now());
        
        // 保存用户
        userMapper.insert(user);
        
        // 转换为VO并返回
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return userVO;
    }
    
    @Override
    public String login(LoginDTO loginDTO) {
        // 根据邮箱查询用户
        Users user = getUserByEmail(loginDTO.getEmail());
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        // 验证密码
        if (!passwordEncoder.matches(loginDTO.getPassword(), user.getPassword())) {
            throw new RuntimeException("Incorrect password");
        }
        
        // 检查账户是否被锁定
        if (user.getIsLocked()) {
            String lockReason = user.getLockReason() != null ? user.getLockReason() : "Account locked";
            throw new RuntimeException("Account is locked: " + lockReason);
        }
        
        // 生成token
        return jwtUtil.generateToken(user.getUserid(), user.getEmail());
    }
    
    @Override
    public Users getUserByEmail(String email) {
        LambdaQueryWrapper<Users> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Users::getEmail, email);
        return userMapper.selectOne(wrapper);
    }
    
    @Override
    @Transactional
    public Users createUser(Users user) {
        user.setCreatedAt(LocalDateTime.now());
        userMapper.insert(user);
        return user;
    }
    
    @Override
    @Transactional
    public Users updateUser(Long id, Users updatedUser) {
        Users user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        user.setName(updatedUser.getName());
        user.setEmail(updatedUser.getEmail());
        user.setAvatar(updatedUser.getAvatar());
        user.setUpdatedAt(LocalDateTime.now());
        // 更新用户角色
        user.setRole(updatedUser.getRole());
        
        userMapper.updateById(user);
        return user;
    }
    
    @Override
    @Transactional
    public void deleteUser(Long userId) {
        // 1. 检查用户是否存在
        Users user = getById(userId);
        if (user == null) {
            throw new RuntimeException("User not found");
        }

        try {
            // 2. 查找用户的所有音乐资源
            LambdaQueryWrapper<MusicResources> musicWrapper = new LambdaQueryWrapper<>();
            musicWrapper.eq(MusicResources::getUserid, userId);
            List<MusicResources> userMusicResources = musicResourceService.list(musicWrapper);

            if (!CollectionUtils.isEmpty(userMusicResources)) {
                List<Long> musicIds = userMusicResources.stream()
                        .map(MusicResources::getMusicid)
                        .collect(Collectors.toList());

                // 3. 查找并删除与这些音乐资源相关的回收站记录
                LambdaQueryWrapper<RecycleBin> recycleBinWrapper = new LambdaQueryWrapper<>();
                recycleBinWrapper.in(RecycleBin::getMusicid, musicIds);
                List<RecycleBin> recycleBinEntries = recycleBinService.list(recycleBinWrapper);
                if (!CollectionUtils.isEmpty(recycleBinEntries)) {
                    List<Long> recycleIds = recycleBinEntries.stream()
                            .map(RecycleBin::getRecycleid)
                            .collect(Collectors.toList());
                    log.info("Deleting recycle bin entries for user {}: {}", userId, recycleIds.toString());
                    recycleBinService.removeByIds(recycleIds);
                }

                // 5. 删除音乐资源记录 (显式删除，避免依赖 cascade)
                log.info("Deleting music resource entries for user {}: {}", userId, musicIds.toString());
                musicResourceService.removeByIds(musicIds);
            }

            // 6. 删除用户
            log.info("Deleting user with ID: {}", userId);
            if (!removeById(userId)) {
                throw new RuntimeException("Failed to delete user from database");
            }

        } catch (Exception e) {
            log.error("Error deleting user with ID: {}", userId, e);
            // 抛出运行时异常以触发事务回滚
            throw new RuntimeException("Failed to delete user and associated data: " + e.getMessage(), e);
        }
    }
    
    @Override
    @Transactional
    public void lockUser(Long id) {
        Users user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        user.setIsLocked(true);
        user.setLockTime(LocalDateTime.now());
        user.setUnlockTime(null);
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.updateById(user);
    }
    
    @Override
    @Transactional
    public void unlockUser(Long id) {
        Users user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        user.setIsLocked(false);
        user.setUnlockTime(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.updateById(user);
    }
    
    @Override
    public UserVO getCurrentUserInfo() {
        // 从UserContext获取当前用户ID
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new RuntimeException("User not logged in");
        }
        
        // 根据ID查询用户，使用显式注入的userMapper
        Users user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        // 转换为VO并返回
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return userVO;
    }
    
    @Override
    @Transactional
    public boolean changePassword(ChangePasswordDTO changePasswordDTO) {
        // 验证参数
        if (!Objects.equals(changePasswordDTO.getNewPassword(), changePasswordDTO.getConfirmPassword())) {
            throw new RuntimeException("New password does not match confirmation password");
        }
        
        // 获取当前用户
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new RuntimeException("User not logged in");
        }
        
        Users user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        // 验证旧密码
        if (!passwordEncoder.matches(changePasswordDTO.getOldPassword(), user.getPassword())) {
            throw new RuntimeException("Incorrect old password");
        }
        
        // 设置新密码
        user.setPassword(passwordEncoder.encode(changePasswordDTO.getNewPassword()));
        user.setUpdatedAt(LocalDateTime.now());
        
        // 更新用户
        return userMapper.updateById(user) > 0;
    }
    
    @Override
    @Transactional
    public UserVO updateCurrentUserInfo(UpdateUserInfoDTO updateUserInfoDTO) {
        // 获取当前用户
        Long userId = UserContext.getCurrentUserId();
        if (userId == null) {
            throw new RuntimeException("User not logged in");
        }
        
        Users user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        // 更新用户信息
        if (StringUtils.hasText(updateUserInfoDTO.getName())) {
            user.setName(updateUserInfoDTO.getName());
        }
        
        if (StringUtils.hasText(updateUserInfoDTO.getAvatar())) {
            user.setAvatar(updateUserInfoDTO.getAvatar());
        }
        
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.updateById(user);
        
        // 转换为VO并返回
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return userVO;
    }
    
    @Override
    @Transactional
    public void lockUserWithReason(Long id, String reason) {
        Users user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        user.setIsLocked(true);
        user.setLockReason(reason);
        user.setLockTime(LocalDateTime.now());
        user.setUnlockTime(null);
        user.setUpdatedAt(LocalDateTime.now());
        userMapper.updateById(user);
    }
    
    @Override
    @Transactional
    public boolean resetUserPassword(Long userId, String newPassword) {
        Users user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("User does not exist");
        }
        
        // 加密新密码
        user.setPassword(passwordEncoder.encode(newPassword));
        user.setUpdatedAt(LocalDateTime.now());
        
        return userMapper.updateById(user) > 0;
    }
    
    private boolean isEmailExists(String email) {
        return getUserByEmail(email) != null;
    }

    @Override
    public boolean isAdmin(Long userId) {
        Users user = userMapper.selectById(userId);
        if (user == null) {
            return false;
        }
        return "ADMIN".equals(user.getRole());
    }

    @Override
    public Users getUserByUsername(String username) {
        LambdaQueryWrapper<Users> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Users::getName, username);
        return userMapper.selectOne(wrapper);
    }

    @Override
    public void sendPasswordResetCode(String email) {
        log.info("Attempting to send password reset code to email: {}", email);
        Users user = getUserByEmail(email);

        if (user == null) {
            log.warn("Password reset requested for non-existent email: {}", email);
            // Do not throw an error to prevent email enumeration
            return; 
        }

        // Generate 6-digit code
        String code = String.format("%06d", new Random().nextInt(999999));
        log.debug("Generated reset code {} for email {}", code, email);

        try {
            // Store code in cache (e.g., valid for 10 minutes)
            Cache cache = cacheManager.getCache("passwordResetCodes");
            if (cache == null) {
                log.error("Cache 'passwordResetCodes' not found. Ensure cache is configured.");
                throw new RuntimeException("Server configuration error.");
            }
            cache.put(email, code);
            log.info("Stored reset code for email {} in cache", email);

            // Send email
            sendEmail(
                email, 
                "Password Reset Verification Code", 
                "Your password reset code is: " + code + "\nIt is valid for 10 minutes."
            );
            log.info("Password reset email successfully sent to {}", email);

        } catch (MailException e) {
            log.error("Failed to send password reset email to {}: {}", email, e.getMessage(), e);
            // Depending on policy, you might want to throw or just log
            throw new RuntimeException("Failed to send verification email. Please try again later.");
        } catch (Exception e) {
            log.error("An unexpected error occurred during password reset code generation/sending for {}: {}", email, e.getMessage(), e);
            throw new RuntimeException("An internal error occurred. Please try again later.");
        }
    }

    @Override
    @Transactional
    public boolean resetPassword(ResetPasswordDTO dto) {
        log.info("Attempting to reset password for email: {}", dto.getEmail());
        // 1. Validate passwords match
        if (!Objects.equals(dto.getNewPassword(), dto.getConfirmPassword())) {
            throw new IllegalArgumentException("New passwords do not match.");
        }

        // 2. Validate verification code from cache
        Cache cache = cacheManager.getCache("passwordResetCodes");
        if (cache == null) {
             log.error("Cache 'passwordResetCodes' not found during password reset.");
             throw new RuntimeException("Server configuration error.");
        }
        String cachedCode = cache.get(dto.getEmail(), String.class);

        if (cachedCode == null) {
            log.warn("No reset code found in cache for email: {}", dto.getEmail());
            throw new RuntimeException("Verification code has expired or is invalid.");
        }

        if (!cachedCode.equals(dto.getCode())) {
            log.warn("Incorrect reset code provided for email: {}. Expected: {}, Got: {}", dto.getEmail(), cachedCode, dto.getCode());
            throw new RuntimeException("Incorrect verification code.");
        }

        // 3. Find user by email
        Users user = getUserByEmail(dto.getEmail());
        if (user == null) {
            // Should ideally not happen if code was valid, but check anyway
            log.error("User not found for email {} during password reset, despite valid code.", dto.getEmail());
            throw new RuntimeException("User associated with this reset request not found."); 
        }

        // 4. Encode new password
        String encodedPassword = passwordEncoder.encode(dto.getNewPassword());

        // 5. Update user's password in DB
        user.setPassword(encodedPassword);
        user.setUpdatedAt(LocalDateTime.now());
        boolean updateSuccess = this.updateById(user);

        if (updateSuccess) {
            log.info("Password successfully reset for user ID: {}", user.getUserid());
            // 6. Remove code from cache after successful reset
            cache.evict(dto.getEmail());
            log.debug("Removed reset code from cache for email {}", dto.getEmail());
            return true;
        } else {
            log.error("Failed to update password in database for user ID: {}", user.getUserid());
            // Consider if specific exception is better
            throw new RuntimeException("Failed to update password in the database."); 
        }
    }

    // Helper method to send email
    private void sendEmail(String to, String subject, String text) throws MailException {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(to);
        message.setSubject(subject);
        message.setText(text);
        
        // Set 'from' address (important for some email providers)
        if (StringUtils.hasText(mailFromAddress)) {
            message.setFrom(mailFromAddress);
        } else {
             log.warn("spring.mail.username or spring.mail.from is not configured. Mail might be rejected by recipient server.");
             // Optionally throw an error if 'from' is mandatory for your setup
        }

        mailSender.send(message);
    }
} 