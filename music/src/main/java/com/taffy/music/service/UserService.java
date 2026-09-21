package com.taffy.music.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.taffy.music.domain.Users;
import com.taffy.music.dto.ChangePasswordDTO;
import com.taffy.music.dto.LoginDTO;
import com.taffy.music.dto.RegisterDTO;
import com.taffy.music.dto.ResetPasswordDTO;
import com.taffy.music.dto.UpdateUserInfoDTO;
import com.taffy.music.vo.UserVO;
import com.taffy.music.repositories.UserRepositories;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

public interface UserService extends IService<Users> {
    
    /**
     * 用户注册
     */
    UserVO register(RegisterDTO registerDTO);
    
    /**
     * 用户登录
     */
    String login(LoginDTO loginDTO);
    
    /**
     * 根据邮箱获取用户
     */
    Users getUserByEmail(String email);
    
    /**
     * 根据ID获取用户
     */
    Optional<Users> getUserById(Long id);
    
    /**
     * 创建用户
     */
    Users createUser(Users user);
    
    /**
     * 更新用户信息
     */
    Users updateUser(Long id, Users updatedUser);
    
    /**
     * 删除用户
     */
    void deleteUser(Long id);
    
    /**
     * 锁定用户
     */
    void lockUser(Long id);
    
    /**
     * 锁定用户（带原因）
     * 
     * @param id 用户ID
     * @param reason 锁定原因
     */
    void lockUserWithReason(Long id, String reason);
    
    /**
     * 解锁用户
     */
    void unlockUser(Long id);
    
    /**
     * 获取当前用户信息
     * 
     * 从UserContext中获取当前用户ID，然后查询用户信息并转换为UserVO
     */
    UserVO getCurrentUserInfo();
    
    /**
     * 修改当前用户密码
     * 
     * @param changePasswordDTO 密码修改DTO
     * @return 是否修改成功
     */
    boolean changePassword(ChangePasswordDTO changePasswordDTO);
    
    /**
     * 更新当前用户信息
     * 
     * @param updateUserInfoDTO 用户信息DTO
     * @return 更新后的用户信息
     */
    UserVO updateCurrentUserInfo(UpdateUserInfoDTO updateUserInfoDTO);
    
    /**
     * 重置用户密码（管理员功能）
     * 
     * @param userId 用户ID
     * @param newPassword 新密码（明文，将在方法内加密）
     * @return 是否重置成功
     */
    boolean resetUserPassword(Long userId, String newPassword);

    /**
     * Sends a password reset verification code to the specified email address.
     *
     * @param email The user's email address.
     * @throws RuntimeException if sending fails or user not found (behavior depends on implementation)
     */
    void sendPasswordResetCode(String email);

    /**
     * Resets the user's password after verifying the reset code.
     *
     * @param resetPasswordDTO DTO containing email, code, and new password.
     * @return true if the password was successfully reset, false otherwise.
     * @throws RuntimeException if validation fails (e.g., code incorrect/expired, user not found)
     */
    boolean resetPassword(ResetPasswordDTO resetPasswordDTO);

    /* 
     * 判断是否是管理员
     * 
     * @param userId 用户ID
     * @return 是否是管理员
     */
    boolean isAdmin(Long userId);

    /**
     * 根据用户名查询用户
     * @param username 用户名
     * @return 用户对象，如果不存在则返回null
     */
    Users getUserByUsername(String username);
}