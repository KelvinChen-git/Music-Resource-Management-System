package com.taffy.music.domain;
import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Entity
@Table(name = "audit_logs")
@Data
public class Auditlogs {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "audit_id")
    private Long auditId;

    @ManyToOne
    @JoinColumn(name = "music_id", nullable = false)
    private MusicResources music;

    @ManyToOne
    @JoinColumn(name = "admin_id", nullable = false)
    private Users admin;

    @Column(name = "action")
    private String action;
    
    @Column(name = "reason")
    private String reason;
    
    @Column(name = "audit_time")
    private LocalDateTime auditTime;
}

