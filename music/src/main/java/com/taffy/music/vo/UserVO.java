package com.taffy.music.vo;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class UserVO {
    private Long userid;
    private String name;
    private String email;
    private String avatar;
    private String role;
    private Boolean verificationStatus;
    private Boolean isLocked;
    private String lockReason;
    private LocalDateTime lockTime;
    private LocalDateTime unlockTime;
} 