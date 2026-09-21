package com.taffy.music.repositories;

import com.taffy.music.domain.MusicResources;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MusicResourceRepository extends JpaRepository<MusicResources, Long> {
    // 默认有删除和查找方法，以下是自定义的查询方法
}