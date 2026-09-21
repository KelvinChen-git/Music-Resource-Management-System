package com.taffy.music.repositories;
import com.taffy.music.domain.MusicResourceTags;
import com.taffy.music.domain.MusicResourceTagId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MusicResourceTagRepository extends JpaRepository<MusicResourceTags, MusicResourceTagId> {
}
