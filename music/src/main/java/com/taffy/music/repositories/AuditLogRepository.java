package com.taffy.music.repositories;
import com.taffy.music.domain.Auditlogs;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AuditLogRepository extends JpaRepository<Auditlogs,Long> {

}
