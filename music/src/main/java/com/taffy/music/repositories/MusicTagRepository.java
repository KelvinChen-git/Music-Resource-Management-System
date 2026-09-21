package com.taffy.music.repositories;
import com.taffy.music.domain.MusicTags;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MusicTagRepository extends JpaRepository<MusicTags,Long> {
}
