package com.taffy.music.repositories;

import com.taffy.music.domain.RecycleBin;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RecycleBinRepository extends JpaRepository<RecycleBin, Long> {
    // 用于访问回收站的数据
}