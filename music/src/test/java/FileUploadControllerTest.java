import com.taffy.music.config.UploadProperties;
import com.taffy.music.controller.FileUploadController;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.service.UploadIntegrityService;
import com.taffy.music.service.FileChunkService;
import com.taffy.music.service.FileUploadService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class FileUploadControllerTest {
    @TempDir Path root;
    FileUploadController controller;
    FileUploadService uploads;
    FileChunkService chunks;
    com.taffy.music.service.UploadAccessService access;

    @BeforeEach void setup() {
        uploads = mock(FileUploadService.class);
        chunks = mock(FileChunkService.class);
        access = mock(com.taffy.music.service.UploadAccessService.class);
        UploadProperties properties = new UploadProperties();
        properties.setTempPath(root.resolve("chunks").toString());
        properties.setPath(root.resolve("uploads").toString());
        properties.setAllowedTypes("mp3");
        controller = new FileUploadController();
        ReflectionTestUtils.setField(controller, "fileUploadService", uploads);
        ReflectionTestUtils.setField(controller, "fileChunkService", chunks);
        ReflectionTestUtils.setField(controller, "uploadProperties", properties);
        ReflectionTestUtils.setField(controller, "uploadIntegrityService",
                new UploadIntegrityService(uploads, chunks, properties, access));
        FileUpload file = new FileUpload();
        file.setId(1L); file.setChunkCount(2); file.setFileSize(6L);
        file.setStatus(0); file.setUploadedChunks(0);
        when(access.requireOwnedLocked(1L)).thenReturn(file);
    }

    @Test void incorrectChunkHashMustNotBeAcknowledged() {
        var result = controller.uploadChunk(1L, 0,
                new MockMultipartFile("chunk", "abc".getBytes()), "0".repeat(32));
        assertNotEquals(200, result.getCode());
        verify(chunks, never()).save(any());
        verify(uploads, never()).updateById(any());
    }

    @Test void failedPersistenceMustNotBeAcknowledged() {
        when(chunks.save(any())).thenReturn(false);
        var result = controller.uploadChunk(1L, 0,
                new MockMultipartFile("chunk", "abc".getBytes()), "900150983cd24fb0d6963f7d28e17f72");
        assertNotEquals(200, result.getCode());
        verify(uploads, never()).updateById(any());
    }
}
