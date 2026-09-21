package com.taffy.music.repositories;
import com.taffy.music.domain.Users;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
@Repository
public interface UserRepositories extends JpaRepository< Users,Long> {
    Users findByEmail(String email);
}
