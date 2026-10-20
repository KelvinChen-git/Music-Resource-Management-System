import cn.hutool.crypto.digest.DigestUtil;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.domain.FileChunk;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.service.FileChunkService;
import com.taffy.music.service.FileUploadService;
import com.taffy.music.service.UploadIntegrityService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class UploadIntegrityServiceTest {
    @TempDir Path root;
    FileUploadService uploads;
    FileChunkService chunks;
    com.taffy.music.service.UploadAccessService access;
    UploadProperties properties;
    UploadIntegrityService service;
    FileUpload upload;
    List<FileChunk> records;

    @BeforeEach void setup() {
        uploads = mock(FileUploadService.class);
        chunks = mock(FileChunkService.class);
        access = mock(com.taffy.music.service.UploadAccessService.class);
        properties = new UploadProperties();
        properties.setTempPath(root.resolve("chunks").toString());
        properties.setPath(root.resolve("uploads").toString());
        service = new UploadIntegrityService(uploads, chunks, properties, access);
        upload = new FileUpload();
        upload.setId(1L); upload.setStatus(0); upload.setUploadedChunks(0);
        upload.setFileName("fixture.mp3"); upload.setFileSize(6L);
        upload.setChunkCount(2); upload.setFileMd5(DigestUtil.md5Hex("abcdef"));
        records = new ArrayList<>();
        when(access.requireOwnedLocked(1L)).thenReturn(upload);
        when(uploads.updateById(any())).thenReturn(true);
        when(chunks.getChunksByFileId(1L)).thenAnswer(call -> new ArrayList<>(records));
        when(chunks.save(any())).thenAnswer(call -> {
            FileChunk record = call.getArgument(0);
            record.setId((long) records.size() + 1); records.add(record); return true;
        });
        when(chunks.updateById(any())).thenReturn(true);
    }

    void send(int index, String content) throws Exception {
        service.uploadChunk(1L, index, new MockMultipartFile("chunk", content.getBytes()), DigestUtil.md5Hex(content));
    }
    void sendBoth() throws Exception { send(0, "abc"); send(1, "def"); }
    long fileCount(Path directory) throws Exception {
        if (!Files.exists(directory)) return 0;
        try (var files = Files.walk(directory)) { return files.filter(Files::isRegularFile).count(); }
    }

    @Test void validatesActualBytesBeforePersistence() throws Exception {
        assertThrows(IllegalArgumentException.class, () -> service.uploadChunk(1L, 0,
                new MockMultipartFile("chunk", "abc".getBytes()), "0".repeat(32)));
        verify(chunks, never()).save(any());
        verify(uploads, never()).updateById(any());
        assertEquals(0, fileCount(root));
    }
    @Test void falseInsertFailsAndRemovesCandidate() throws Exception {
        doReturn(false).when(chunks).save(any());
        assertThrows(IllegalStateException.class, () -> send(0, "abc"));
        verify(uploads, never()).updateById(any());
        assertEquals(0, fileCount(root));
    }
    @Test void insertExceptionPropagatesAndRemovesCandidate() throws Exception {
        doThrow(new IllegalStateException("database unavailable")).when(chunks).save(any());
        assertThrows(IllegalStateException.class, () -> send(0, "abc"));
        assertEquals(0, fileCount(root));
        verify(uploads, never()).updateById(any());
    }
    @Test void falseCounterUpdateFailsAndRemovesCandidate() throws Exception {
        when(uploads.updateById(any())).thenReturn(false);
        assertThrows(IllegalStateException.class, () -> send(0, "abc"));
        assertEquals(0, fileCount(root));
    }
    @Test void acknowledgedChunkExistsOnDiskAndInPersistedRecords() throws Exception {
        send(0, "abc");
        assertEquals(1, records.size()); assertEquals(1, upload.getUploadedChunks());
        assertEquals("abc", Files.readString(Path.of(records.get(0).getChunkPath())));
        assertEquals(DigestUtil.md5Hex("abc"), records.get(0).getChunkMd5());
    }
    @Test void retryAfterServiceRecreationDoesNotDuplicateOrTrustCounter() throws Exception {
        send(0, "abc");
        upload.setUploadedChunks(99);
        service = new UploadIntegrityService(uploads, chunks, properties, access);
        send(0, "abc");
        assertEquals(1, records.size()); assertEquals(1, upload.getUploadedChunks());
        verify(chunks, times(1)).save(any());
        assertEquals(1, fileCount(root));
    }
    @Test void moreThanOldBatchThresholdStillPersistsExactlyOnce() throws Exception {
        upload.setChunkCount(12); upload.setFileSize(12L);
        for (int i = 0; i < 12; i++) send(i, "a");
        assertEquals(12, upload.getUploadedChunks());
        verify(chunks, times(12)).save(any());
        verify(chunks, never()).saveBatch(anyCollection());
    }
    @Test void conflictingRetryCannotOverwriteAcceptedBytes() throws Exception {
        send(0, "abc");
        Path original = Path.of(records.get(0).getChunkPath());
        assertThrows(IllegalArgumentException.class, () -> send(0, "xyz"));
        assertEquals("abc", Files.readString(original));
        assertEquals(1, upload.getUploadedChunks()); assertEquals(1, fileCount(root));
    }
    @Test void missingChunkCanBeRepairedUsingSameContentWithoutNewRow() throws Exception {
        send(0, "abc"); Files.delete(Path.of(records.get(0).getChunkPath()));
        send(0, "abc");
        assertEquals(1, records.size()); assertEquals(1, upload.getUploadedChunks());
        assertEquals("abc", Files.readString(Path.of(records.get(0).getChunkPath())));
        verify(chunks).updateById(any());
    }
    @Test void corruptedChunkCanBeRepairedAndOldPathIsRemoved() throws Exception {
        send(0, "abc"); Path old = Path.of(records.get(0).getChunkPath());
        Files.writeString(old, "xyz"); send(0, "abc");
        assertFalse(Files.exists(old)); assertEquals(1, fileCount(root));
        assertEquals("abc", Files.readString(Path.of(records.get(0).getChunkPath())));
    }
    @Test void retryPromotesIncompleteRowOnlyAfterSuccessfulPersistence() throws Exception {
        send(0, "abc"); records.get(0).setStatus(0);
        send(0, "abc");
        assertEquals(1, records.get(0).getStatus());
        assertEquals(1, upload.getUploadedChunks());
        verify(chunks).updateById(any());
        assertEquals(1, fileCount(root));
    }
    @Test void uncertainTransactionOutcomePreservesFileForReconciliation() throws Exception {
        TransactionSynchronizationManager.initSynchronization();
        try {
            send(0, "abc");
            for (var callback : TransactionSynchronizationManager.getSynchronizations())
                callback.afterCompletion(TransactionSynchronization.STATUS_UNKNOWN);
            assertEquals(1, fileCount(root));
        } finally { TransactionSynchronizationManager.clearSynchronization(); }
    }
    @Test void invalidIndexesAreRejectedWithoutWrites() {
        assertThrows(IllegalArgumentException.class, () -> send(-1, "abc"));
        assertThrows(IllegalArgumentException.class, () -> send(2, "abc"));
        verify(chunks, never()).save(any());
    }
    @Test void completedUploadRejectsAdditionalChunks() {
        upload.setStatus(1);
        assertThrows(IllegalArgumentException.class, () -> send(0, "abc"));
        verify(chunks, never()).save(any());
    }
    @Test void mergeValidatesBytesAndRepeatedMergeReusesOneFile() throws Exception {
        sendBoth(); String path = service.merge(1L);
        assertEquals("abcdef", Files.readString(root.resolve("uploads").resolve(path)));
        assertEquals(1, upload.getStatus()); assertEquals(path, service.merge(1L));
        assertEquals(0, fileCount(root.resolve("chunks")));
        assertEquals(1, fileCount(root.resolve("uploads")));
    }
    @Test void incorrectWholeFileHashDoesNotPublishOrDeleteChunks() throws Exception {
        sendBoth(); upload.setFileMd5("0".repeat(32));
        assertThrows(IllegalArgumentException.class, () -> service.merge(1L));
        assertEquals(0, upload.getStatus()); assertEquals(2, fileCount(root.resolve("chunks")));
        assertEquals(0, fileCount(root.resolve("uploads")));
    }
    @Test void incorrectWholeFileSizeDoesNotPublish() throws Exception {
        sendBoth(); upload.setFileSize(7L);
        assertThrows(IllegalArgumentException.class, () -> service.merge(1L));
        assertEquals(0, upload.getStatus()); assertEquals(2, fileCount(root.resolve("chunks")));
        assertEquals(0, fileCount(root.resolve("uploads")));
    }
    @Test void corruptedDiskChunkDoesNotPublish() throws Exception {
        sendBoth(); Files.writeString(Path.of(records.get(0).getChunkPath()), "xyz");
        assertThrows(IllegalArgumentException.class, () -> service.merge(1L));
        assertEquals(0, upload.getStatus()); assertEquals(0, fileCount(root.resolve("uploads")));
    }
    @Test void incompleteAndNonContiguousSetsDoNotPublish() throws Exception {
        send(0, "abc");
        assertThrows(IllegalArgumentException.class, () -> service.merge(1L));
        send(1, "def"); records.get(1).setChunkIndex(2);
        assertThrows(IllegalArgumentException.class, () -> service.merge(1L));
        assertEquals(0, fileCount(root.resolve("uploads")));
    }
    @Test void failedCompletionPersistencePreservesSourcesAndRemovesTarget() throws Exception {
        sendBoth(); when(uploads.updateById(any())).thenReturn(false);
        assertThrows(IllegalStateException.class, () -> service.merge(1L));
        assertEquals(2, fileCount(root.resolve("chunks")));
        assertEquals(0, fileCount(root.resolve("uploads")));
    }
    @Test void transactionRollbackRemovesNewChunkFile() throws Exception {
        TransactionSynchronizationManager.initSynchronization();
        try {
            send(0, "abc");
            for (var callback : TransactionSynchronizationManager.getSynchronizations())
                callback.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK);
            assertEquals(0, fileCount(root));
        } finally { TransactionSynchronizationManager.clearSynchronization(); }
    }
    @Test void mergeCleanupWaitsForCommitAndRollbackPreservesSources() throws Exception {
        sendBoth(); TransactionSynchronizationManager.initSynchronization();
        try {
            service.merge(1L);
            assertEquals(2, fileCount(root.resolve("chunks")));
            for (var callback : TransactionSynchronizationManager.getSynchronizations())
                callback.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK);
            assertEquals(2, fileCount(root.resolve("chunks")));
            assertEquals(0, fileCount(root.resolve("uploads")));
        } finally { TransactionSynchronizationManager.clearSynchronization(); }
    }
    @Test void mergeCommitCleansSourcesAndKeepsPublishedTarget() throws Exception {
        sendBoth(); TransactionSynchronizationManager.initSynchronization();
        try {
            service.merge(1L);
            for (var callback : TransactionSynchronizationManager.getSynchronizations()) callback.afterCommit();
            for (var callback : TransactionSynchronizationManager.getSynchronizations())
                callback.afterCompletion(TransactionSynchronization.STATUS_COMMITTED);
            assertEquals(0, fileCount(root.resolve("chunks")));
            assertEquals(1, fileCount(root.resolve("uploads")));
        } finally { TransactionSynchronizationManager.clearSynchronization(); }
    }
}
