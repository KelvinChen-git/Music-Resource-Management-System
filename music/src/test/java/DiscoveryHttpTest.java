import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.discovery.*;
import com.taffy.music.domain.*;
import com.taffy.music.interceptor.JwtAuthenticationInterceptor;
import com.taffy.music.mapper.DiscoveryTagMapper;
import com.taffy.music.service.*;
import com.taffy.music.utils.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.*;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

/** HTTP/service boundary fixtures, not a real database or semantic model. */
class DiscoveryHttpTest {
    @TempDir Path root;
    final ObjectMapper json = new ObjectMapper();
    final byte[] bytes = "abcdefghijklmnopqrstuvwxyz0123456789".getBytes();
    final MusicResourceService music = mock(MusicResourceService.class);
    final FileUploadService uploads = mock(FileUploadService.class);
    final UserService users = mock(UserService.class);
    final DiscoveryTagMapper tags = mock(DiscoveryTagMapper.class);
    final DiscoveryClient worker = mock(DiscoveryClient.class);
    DiscoveryProperties config;
    DiscoveryService service;
    MockMvc mvc;
    MusicResources record;
    FileUpload upload;
    JwtUtil jwt;
    String md5, sha;
    Users owner, other, admin;

    @BeforeEach void setup() throws Exception {
        UserContext.clear(); Files.write(root.resolve("fixture.mp3"), bytes);
        md5 = HexFormat.of().formatHex(MessageDigest.getInstance("MD5").digest(bytes));
        sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        record = new MusicResources(); record.setMusicid(42L); record.setUserid(1L); record.setCategoryid(7L);
        record.setApprovalStatus("approved"); record.setIsDeleted(false); record.setFilePath("fixture.mp3");
        record.setTitle("Current title"); record.setArtist("Synthetic fixture"); record.setFormat("mp3");
        upload = new FileUpload(); upload.setId(3L); upload.setFilePath(record.getFilePath()); upload.setFileType("mp3");
        upload.setFileMd5(md5); upload.setFileSize((long) bytes.length); upload.setDeleted(false); upload.setStatus(1);
        owner = user(1, "USER"); other = user(2, "USER"); admin = user(3, "ADMIN");
        when(users.getById(1L)).thenReturn(owner); when(users.getById(2L)).thenReturn(other); when(users.getById(3L)).thenReturn(admin);
        when(music.list(any(Wrapper.class))).thenReturn(List.of(record)); when(music.getById(42L)).thenReturn(record);
        when(uploads.list(any(Wrapper.class))).thenReturn(List.of(upload));
        when(tags.matching(anyList(), anyBoolean(), anyInt())).thenReturn(List.of(42L));
        config = new DiscoveryProperties(); config.setEnabled(true); config.setAllowSynthetic(true);
        config.setIndexVersion("test-index-v1"); config.setModelVersion("test-model-v1");
        UploadProperties paths = new UploadProperties(); paths.setPath(root.toString());
        var access = new MediaAccessService(music, uploads, users, paths);
        service = new DiscoveryService(music, uploads, access, tags, worker, config, json);
        when(worker.search(any())).thenAnswer(call -> {
            ObjectNode response = response();
            if (call.getArgument(0, JsonNode.class).path("allowed_tracks").isEmpty()) response.putArray("results");
            return response;
        });
        jwt = new JwtUtil(); ReflectionTestUtils.setField(jwt, "secret", "a".repeat(128));
        ReflectionTestUtils.setField(jwt, "expiration", 60000L);
        var interceptor = new JwtAuthenticationInterceptor(); ReflectionTestUtils.setField(interceptor, "jwtUtil", jwt);
        mvc = MockMvcBuilders.standaloneSetup(new DiscoveryController(service, json)).addInterceptors(interceptor).build();
    }
    @AfterEach void cleanup() { UserContext.clear(); }
    private Users user(long id, String role) {
        Users user = new Users(); user.setUserid(id); user.setRole(role); user.setIsLocked(false); return user;
    }
    private ObjectNode response() {
        ObjectNode value = json.createObjectNode();
        value.put("index_version", "test-index-v1").put("model_version", "test-model-v1")
                .put("engine_kind", "synthetic_fixture").put("retrieval_mode", "segment");
        value.putObject("timings_ms").put("query_encoding", 1).put("retrieval", 1);
        var row = value.putArray("results").addObject();
        row.put("track_id", "42").put("duration_ms", 10000).put("content_bytes", bytes.length)
                .put("content_md5", md5).put("content_sha256", sha).put("score", .8);
        row.putArray("segments").addObject().put("segment_id", "42:0").put("start_ms", 0).put("end_ms", 1000).put("score", .8);
        return value;
    }
    private String token(int id) { return jwt.generateToken((long) id, "fixture@example.invalid"); }
    private MvcResult search(String body, int user) throws Exception {
        var request = post("/discovery/search").contentType("application/json").content(body);
        if (user != 0) request.header("Authorization", "Bearer " + token(user));
        return mvc.perform(request).andReturn();
    }
    private String query() { return "{\"query\":{\"kind\":\"text\",\"text\":\"synthetic fixture\"}}"; }
    private JsonNode body(MvcResult result) throws Exception { return json.readTree(result.getResponse().getContentAsByteArray()); }
    private String media() { return "/discovery/tracks/42/media?content_md5=" + md5 + "&content_sha256=" + sha; }

    @Test void anonymousAndInvalidJwtUse401Envelope() throws Exception {
        MvcResult result = search(query(), 0);
        assertEquals(401, result.getResponse().getStatus());
        assertEquals("unauthorized", body(result).path("data").path("error_type").asText());
        assertNotNull(result.getResponse().getHeader("Cache-Control"));
        result = mvc.perform(post("/discovery/search").header("Authorization", "Bearer invalid").contentType("application/json").content(query())).andReturn();
        assertEquals(401, result.getResponse().getStatus()); verifyNoInteractions(worker);
    }
    @Test void approvedResultsUseCurrentMetadataAndStringIds() throws Exception {
        MvcResult result = search(query(), 2); assertEquals(200, result.getResponse().getStatus());
        JsonNode row = body(result).path("data").path("results").get(0);
        assertTrue(row.path("track_id").isTextual()); assertEquals("Current title", row.path("title").asText());
        assertTrue(row.path("preview_url").asText().startsWith("/api/discovery/tracks/42/media?content_md5="));
    }
    @Test void pendingRejectedDeletedExcludedEvenForOwnerOrAdmin() throws Exception {
        for (String state : List.of("pending", "rejected", "unknown")) {
            record.setApprovalStatus(state);
            for (int user : List.of(1, 3)) assertTrue(body(search(query(), user)).path("data").path("results").isEmpty());
        }
        record.setApprovalStatus("approved"); record.setIsDeleted(true);
        assertTrue(body(search(query(), 1)).path("data").path("results").isEmpty());
    }
    @Test void visibilityRevokedDuringWorkerCallIsRechecked() throws Exception {
        doAnswer(call -> { record.setApprovalStatus("rejected"); return response(); }).when(worker).search(any());
        assertTrue(body(search(query(), 1)).path("data").path("results").isEmpty());
    }
    @Test void accountLockedDuringWorkerCallIsForbidden() throws Exception {
        doAnswer(call -> { other.setIsLocked(true); return response(); }).when(worker).search(any());
        assertEquals(403, search(query(), 2).getResponse().getStatus());
    }
    @Test void metadataFiltersAndTagAllAreAppliedTwice() throws Exception {
        String filtered = "{\"query\":{\"kind\":\"text\",\"text\":\"x\"},\"filters\":{\"category_id\":\"7\",\"tag_ids\":[\"8\",\"8\",\"9\"],\"tag_match\":\"all\"}}";
        assertEquals(200, search(filtered, 1).getResponse().getStatus());
        verify(tags, times(2)).matching(List.of(8L, 9L), true, 2);
        when(tags.matching(anyList(), anyBoolean(), anyInt())).thenReturn(List.of());
        assertTrue(body(search(filtered, 1)).path("data").path("results").isEmpty());
    }
    @Test void badBodyModesUnknownDuplicateAndOversizedRejected() throws Exception {
        for (String raw : List.of("{}", "{", "{\"query\":1}", query().replace("text\":\"synthetic fixture", "text\":\""),
                query().replace("}}", "},\"top_k\":0}"), query().replace("}}", "},\"retrieval_mode\":\"hybrid\"}"),
                query().replace("}}", "},\"extra\":true}"), "{\"query\":{},\"query\":{}}", query()+"{}"))
            assertEquals(400, search(raw, 1).getResponse().getStatus(), raw);
        assertEquals(413, search(" ".repeat(8193), 1).getResponse().getStatus());
    }
    @Test void disabledAndSyntheticWithoutOptInFailClosed() throws Exception {
        config.setEnabled(false); assertEquals(503, search(query(), 1).getResponse().getStatus()); verifyNoInteractions(worker);
        config.setEnabled(true); config.setAllowSynthetic(false); assertEquals(503, search(query(), 1).getResponse().getStatus());
    }
    @Test void backendVersionUnknownIdAndInvalidTimeAreNotReturned() throws Exception {
        for (String error : List.of("version", "id", "time", "md5")) {
            var value = response();
            if (error.equals("version")) value.put("model_version", "different");
            var row = (ObjectNode) value.path("results").get(0);
            if (error.equals("id")) row.put("track_id", "99");
            if (error.equals("time")) ((ObjectNode) row.path("segments").get(0)).put("end_ms", 10001);
            if (error.equals("md5")) row.put("content_md5", "0".repeat(32));
            doReturn(value).when(worker).search(any());
            assertEquals(503, search(query(), 1).getResponse().getStatus(), error);
        }
    }
    @Test void workerFailureDoesNotLeakInternalPaths() throws Exception {
        doThrow(new RuntimeException("/secret/path token=do-not-return")).when(worker).search(any());
        var result = search(query(), 1);
        assertEquals(503, result.getResponse().getStatus()); assertFalse(result.getResponse().getContentAsString().contains("secret"));
    }
    @Test void previewUsesActualRangeAndNoStore() throws Exception {
        var result = mvc.perform(get(media()).header("Authorization", "Bearer " + token(2)).header("Range", "bytes=2-5")).andReturn();
        assertEquals(206, result.getResponse().getStatus()); assertArrayEquals(Arrays.copyOfRange(bytes, 2, 6), result.getResponse().getContentAsByteArray());
        assertTrue(result.getResponse().getHeader("Cache-Control").contains("no-store"));
    }
    @Test void previewRechecksUploadRevocationAfterHash() throws Exception {
        doReturn(List.of(upload), List.of()).when(uploads).list(any(Wrapper.class));
        var result = mvc.perform(get(media()).header("Authorization", "Bearer " + token(2))).andReturn();
        assertEquals(404, result.getResponse().getStatus());
        assertEquals("media_unavailable", body(result).path("data").path("error_type").asText());
    }
    @Test void previewRejectsAnonymousHiddenAndStaleContent() throws Exception {
        assertEquals(401, mvc.perform(get(media())).andReturn().getResponse().getStatus());
        record.setApprovalStatus("pending");
        assertEquals(404, mvc.perform(get(media()).header("Authorization", "Bearer " + token(1))).andReturn().getResponse().getStatus());
        record.setApprovalStatus("approved");
        assertEquals(409, mvc.perform(get(media().replace(sha, "0".repeat(64))).header("Authorization", "Bearer " + token(1))).andReturn().getResponse().getStatus());
        Files.write(root.resolve("fixture.mp3"), "other bytes".getBytes());
        assertEquals(409, mvc.perform(get(media()).header("Authorization", "Bearer " + token(1))).andReturn().getResponse().getStatus());
    }
}
