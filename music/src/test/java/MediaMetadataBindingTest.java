import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.MusicResourceMapper;
import com.taffy.music.service.FileUploadService;
import com.taffy.music.service.UserService;
import com.taffy.music.service.impl.MusicResourceServiceImpl;
import com.taffy.music.utils.UserContext;
import com.taffy.music.vo.MusicMetadataVO;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class MediaMetadataBindingTest {
    @AfterEach void clear() { UserContext.clear(); }
    void rejectBinding(String status, boolean deleted, boolean owner, boolean admin) {
        UserContext.setContext(1L,"fixture@example.invalid");
        var mapper = mock(MusicResourceMapper.class);
        var files = mock(FileUploadService.class);
        var users = mock(UserService.class);
        var service = new MusicResourceServiceImpl();
        ReflectionTestUtils.setField(service,"baseMapper",mapper);
        ReflectionTestUtils.setField(service,"fileUploadService",files);
        ReflectionTestUtils.setField(service,"userService",users);
        FileUpload upload = new FileUpload();
        upload.setStatus(1); upload.setFileType("mp3"); upload.setFilePath("protected.mp3");
        var access = mock(com.taffy.music.service.UploadAccessService.class);
        ReflectionTestUtils.setField(service,"uploadAccessService",access);
        when(access.requireOwnedLocked(9L)).thenReturn(upload);
        MusicResources record = new MusicResources();
        record.setUserid(owner?1L:2L); record.setApprovalStatus(status); record.setIsDeleted(deleted);
        when(mapper.selectList(any(Wrapper.class))).thenReturn(List.of(record));
        Users viewer = new Users(); viewer.setUserid(1L); viewer.setRole(admin?"ADMIN":"USER"); viewer.setIsLocked(false);
        when(users.getById(1L)).thenReturn(viewer);
        RuntimeException error = assertThrows(RuntimeException.class,
                () -> service.parseAndSaveMetadata(9L,new MusicMetadataVO()));
        assertEquals("文件不可用",error.getMessage());
        verify(mapper,never()).insert(any(MusicResources.class));
    }
    @Test void outsiderCannotClonePendingFileIntoOwnResource() { rejectBinding("pending",false,false,false); }
    @Test void rejectedOwnerCannotResetModerationByCloning() { rejectBinding("rejected",false,true,false); }
    @Test void administratorCannotReviveDeletedBytesByCloning() { rejectBinding("approved",true,false,true); }
    @Test void unknownStatusCannotBeCloned() { rejectBinding("unknown",false,false,true); }
}
