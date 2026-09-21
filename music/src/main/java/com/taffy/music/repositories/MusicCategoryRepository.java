package com.taffy.music.repositories;
import com.taffy.music.domain.MusicCategory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MusicCategoryRepository extends JpaRepository<MusicCategory, Integer> {
}
