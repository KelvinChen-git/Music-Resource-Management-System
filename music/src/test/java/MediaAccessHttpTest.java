import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.config.GlobalExceptionHandler;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.controller.FileUploadController;
import com.taffy.music.controller.MusicResourceController;
import com.taffy.music.controller.StaticUploadController;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.interceptor.JwtAuthenticationInterceptor;
import com.taffy.music.service.*;
import com.taffy.music.utils.JwtUtil;
import com.taffy.music.utils.UserContext;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpMethod;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.util.pattern.PathPatternParser;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;
import java.util.zip.ZipInputStream;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

class MediaAccessHttpTest {
    @TempDir Path root;
    final byte[] audio = "abcdefghijklmnopqrstuvwxyz0123456789".getBytes();

    class Fixture {
        final MusicResourceService music = mock(MusicResourceService.class);
        final FileUploadService uploads = mock(FileUploadService.class);
        final UserService users = mock(UserService.class);
        final MusicResources record = new MusicResources();
        final FileUpload upload = new FileUpload();
        final Users owner = user(1, "USER"), other = user(2, "USER"), admin = user(3, "ADMIN");
        final JwtUtil jwt = new JwtUtil();
        final MockMvc mvc;
        final Path directory;
        final MediaAccessService access;
        Fixture() throws Exception {
            UserContext.clear();
            directory = Files.createTempDirectory(root, "media-");
            Files.write(directory.resolve("track.mp3"), audio);
            UploadProperties properties = new UploadProperties();
            properties.setPath(directory.toString());
            access = new MediaAccessService(music, uploads, users, properties);
            record.setMusicid(42L); record.setUserid(1L); record.setApprovalStatus("approved");
            record.setIsDeleted(false); record.setFilePath("track.mp3"); record.setTitle("fixture"); record.setFormat("mp3");
            upload.setId(9L); upload.setStatus(1); upload.setDeleted(false);
            upload.setFilePath("track.mp3"); upload.setFileName("fixture.mp3");
            when(music.getById(42L)).thenReturn(record);
            when(music.list(any(Wrapper.class))).thenAnswer(call -> List.of(record));
            when(uploads.getById(9L)).thenReturn(upload);
            when(users.getById(1L)).thenReturn(owner);
            when(users.getById(2L)).thenReturn(other);
            when(users.getById(3L)).thenReturn(admin);
            ReflectionTestUtils.setField(jwt, "secret", "a".repeat(128));
            ReflectionTestUtils.setField(jwt, "expiration", 60000L);
            JwtAuthenticationInterceptor interceptor = new JwtAuthenticationInterceptor();
            ReflectionTestUtils.setField(interceptor, "jwtUtil", jwt);
            MusicResourceController resource = new MusicResourceController();
            ReflectionTestUtils.setField(resource, "mediaAccessService", access);
            ReflectionTestUtils.setField(resource, "musicResourceService", music);
            ReflectionTestUtils.setField(resource, "objectMapper", new com.fasterxml.jackson.databind.ObjectMapper());
            FileUploadController raw = new FileUploadController();
            ReflectionTestUtils.setField(raw, "mediaAccessService", access);
            ReflectionTestUtils.setField(raw, "uploadProperties", properties);
            mvc = MockMvcBuilders.standaloneSetup(resource, raw, new StaticUploadController(access))
                    .setPatternParser(new PathPatternParser())
                    .setControllerAdvice(new GlobalExceptionHandler()).addInterceptors(interceptor).build();
        }
        MockHttpServletRequestBuilder request(String method, String path, int viewer) {
            var request = org.springframework.test.web.servlet.request.MockMvcRequestBuilders.request(HttpMethod.valueOf(method), path);
            if (viewer != 0) request.header("Authorization", "Bearer " + jwt.generateToken((long)viewer, "test@example.invalid"));
            return request;
        }
        MvcResult perform(String path, int viewer) throws Exception { return mvc.perform(request("GET", path, viewer)).andReturn(); }
    }
    Users user(long id, String role) {
        Users user = new Users(); user.setUserid(id); user.setRole(role); user.setIsLocked(false); return user;
    }
    void status(MvcResult result, int expected) throws Exception {
        assertEquals(expected, result.getResponse().getStatus(), result.getResponse().getContentAsString());
        assertEquals("private, no-store", result.getResponse().getHeader("Cache-Control"));
        assertEquals("Authorization", result.getResponse().getHeader("Vary"));
        assertEquals("nosniff", result.getResponse().getHeader("X-Content-Type-Options"));
    }

    @TestFactory Stream<DynamicTest> identityStateAndTransportMatrix() {
        return Stream.of("approved", "pending", "rejected", "deleted").flatMap(state ->
            Stream.of(0, 1, 2, 3).flatMap(viewer ->
                Stream.of("/music-resources/42/file", "/file/download/9", "/uploads/track.mp3").flatMap(path ->
                    Stream.of("GET", "HEAD", "RANGE").map(method -> DynamicTest.dynamicTest(
                        state + "/viewer=" + viewer + path + "/" + method, () -> {
                            Fixture f = new Fixture();
                            f.record.setApprovalStatus(state.equals("deleted") ? "approved" : state);
                            f.record.setIsDeleted(state.equals("deleted"));
                            var request = f.request(method.equals("RANGE") ? "GET" : method, path, viewer);
                            if (method.equals("RANGE")) request.header("Range", "bytes=0-7");
                            boolean allowed = viewer != 0 && !path.startsWith("/uploads/") && !state.equals("deleted")
                                    && (state.equals("approved") || viewer == 3 || (state.equals("pending") && viewer == 1));
                            MvcResult response = f.mvc.perform(request).andReturn();
                            status(response, viewer == 0 ? 401 : allowed ? (method.equals("RANGE") ? 206 : 200) : 404);
                            if (allowed && method.equals("RANGE")) {
                                assertEquals("bytes 0-7/36", response.getResponse().getHeader("Content-Range"));
                                assertArrayEquals("abcdefgh".getBytes(), response.getResponse().getContentAsByteArray());
                            }
                            if (!allowed) assertFalse(response.getResponse().getContentAsString().contains(new String(audio)));
                            verify(f.music, never()).incrementPlayCount(anyLong());
                            assertNull(UserContext.getCurrentUserId());
                        })))));
    }

    @Test void deniedAndHeadPlaybackCannotIncrementCounters() throws Exception {
        Fixture f = new Fixture();
        status(f.perform("/music-resources/42/file?pay=1", 0), 401);
        f.record.setApprovalStatus("rejected");
        status(f.perform("/music-resources/42/file?pay=1", 1), 404);
        f.record.setApprovalStatus("approved");
        status(f.mvc.perform(f.request("HEAD", "/music-resources/42/file?pay=1", 1)).andReturn(), 200);
        verify(f.music, never()).incrementPlayCount(anyLong());
        status(f.perform("/music-resources/42/file?pay=1", 1), 200);
        verify(f.music).incrementPlayCount(42L);
    }
    @Test void missingPhysicalFileCannotIncrementCounter() throws Exception {
        Fixture f = new Fixture(); Files.delete(f.directory.resolve("track.mp3"));
        status(f.perform("/music-resources/42/file?pay=1", 1), 404);
        verify(f.music, never()).incrementPlayCount(anyLong());
    }
    @Test void invalidJwtAndQueryTokensCannotAuthorizeMedia() throws Exception {
        Fixture f = new Fixture();
        status(f.mvc.perform(get("/music-resources/42/file").header("Authorization", "Bearer invalid")).andReturn(), 401);
        status(f.perform("/music-resources/42/file?token=" + f.jwt.generateToken(1L, "test@example.invalid"), 0), 401);
    }
    @Test void lockedDeletedAndDemotedUsersAreRecheckedWithSameJwt() throws Exception {
        Fixture f = new Fixture();
        status(f.perform("/music-resources/42/file", 1), 200);
        f.owner.setIsLocked(true);
        status(f.perform("/music-resources/42/file", 1), 403);
        when(f.users.getById(1L)).thenReturn(null);
        status(f.perform("/music-resources/42/file", 1), 401);
        f.record.setApprovalStatus("pending");
        status(f.perform("/music-resources/42/file", 3), 200);
        f.admin.setRole("USER");
        status(f.perform("/music-resources/42/file", 3), 404);
    }
    @Test void sharedPathRechecksEveryReferenceAndNeverTreatsDeletedAsOrphan() throws Exception {
        Fixture f = new Fixture(); f.record.setIsDeleted(true);
        status(f.perform("/file/download/9", 3), 404);
        when(f.music.list(any(Wrapper.class))).thenReturn(List.of());
        status(f.perform("/file/download/9", 1), 404);
        status(f.perform("/file/download/9", 3), 200);
        f.upload.setDeleted(true);
        status(f.perform("/file/download/9", 3), 404);
    }
    @Test void traversalAbsoluteAndEscapingSymlinkPathsAreRejected() throws Exception {
        Fixture f = new Fixture();
        Path outside = Files.write(root.resolve("outside.mp3"), audio);
        for (String path : List.of("../outside.mp3", outside.toString(), "x\\..\\outside.mp3")) {
            f.record.setFilePath(path);
            status(f.perform("/music-resources/42/file", 1), 404);
        }
        Files.createSymbolicLink(f.directory.resolve("escape.mp3"), outside);
        f.record.setFilePath("escape.mp3");
        status(f.perform("/music-resources/42/file", 1), 404);
    }
    @Test void registeredRasterAvatarRemainsPublicButMusicAndUnregisteredImagesDoNot() throws Exception {
        Fixture f = new Fixture();
        javax.imageio.ImageIO.write(new BufferedImage(1,1,BufferedImage.TYPE_INT_RGB), "png", f.directory.resolve("avatar.png").toFile());
        when(f.users.count(any(Wrapper.class))).thenReturn(1L);
        status(f.perform("/uploads/avatar.png", 0), 200);
        when(f.music.count(any(Wrapper.class))).thenReturn(1L);
        status(f.perform("/uploads/avatar.png", 1), 404);
        when(f.music.count(any(Wrapper.class))).thenReturn(0L);
        when(f.users.count(any(Wrapper.class))).thenReturn(0L);
        status(f.perform("/uploads/avatar.png", 0), 401);
        Files.write(f.directory.resolve("fake.png"), audio);
        when(f.users.count(any(Wrapper.class))).thenReturn(1L);
        status(f.perform("/uploads/fake.png", 1), 404);
    }
    @Test void rangeFailuresAndSuccessesDoNotIncrementPlayback() throws Exception {
        Fixture f = new Fixture();
        status(f.mvc.perform(f.request("GET", "/music-resources/42/file?pay=1", 1)
                .header("Range", "bytes=100-200")).andReturn(), 416);
        status(f.mvc.perform(f.request("GET", "/music-resources/42/file?pay=1", 1)
                .header("Range", "bytes=0-7")).andReturn(), 206);
        verify(f.music, never()).incrementPlayCount(anyLong());
    }
    @Test void avatarAliasesCannotAvoidPathAssociationChecks() throws Exception {
        Fixture f = new Fixture();
        Files.createDirectories(f.directory.resolve("nested"));
        javax.imageio.ImageIO.write(new BufferedImage(1,1,BufferedImage.TYPE_INT_RGB), "png",
                f.directory.resolve("nested/avatar.png").toFile());
        when(f.users.count(any(Wrapper.class))).thenReturn(1L);
        assertNull(f.access.publicAvatar("nested//avatar.png"));
        Files.createSymbolicLink(f.directory.resolve("alias.png"), f.directory.resolve("nested/avatar.png"));
        assertNull(f.access.publicAvatar("alias.png"));
    }
    @org.springframework.context.annotation.Configuration
    @org.springframework.web.servlet.config.annotation.EnableWebMvc
    static class ActualMvc {}

    @Test void actualMvcConfigurationAuthenticatesAllPrivateMediaRoutesAndKeepsAvatars() throws Exception {
        Fixture f = new Fixture();
        var context = new org.springframework.web.context.support.GenericWebApplicationContext();
        context.setServletContext(new org.springframework.mock.web.MockServletContext());
        org.springframework.context.annotation.AnnotationConfigUtils.registerAnnotationConfigProcessors(context);
        context.getEnvironment().getPropertySources().addFirst(new org.springframework.core.env.MapPropertySource(
                "test", java.util.Map.of("upload.path", f.directory.toString(), "jwt.secret", "a".repeat(128), "jwt.expiration", "60000")));
        context.registerBean(ActualMvc.class);
        context.registerBean(com.taffy.music.config.WebMvcConfig.class);
        context.registerBean(GlobalExceptionHandler.class);
        context.registerBean(JwtUtil.class, () -> f.jwt);
        context.registerBean(JwtAuthenticationInterceptor.class);
        context.registerBean(MediaAccessService.class, () -> f.access);
        context.registerBean(MusicResourceService.class, () -> f.music);
        context.registerBean(FileUploadService.class, () -> f.uploads);
        context.registerBean(UserService.class, () -> f.users);
        context.registerBean(com.taffy.music.mapper.MusicResourceMapper.class,
                () -> mock(com.taffy.music.mapper.MusicResourceMapper.class));
        context.registerBean(FileChunkService.class, () -> mock(FileChunkService.class));
        context.registerBean(UploadIntegrityService.class, () -> mock(UploadIntegrityService.class));
        context.registerBean(UploadProperties.class, () -> {
            var properties = new UploadProperties(); properties.setPath(f.directory.toString()); return properties;
        });
        context.registerBean(com.fasterxml.jackson.databind.ObjectMapper.class);
        context.registerBean(MusicResourceController.class);
        context.registerBean(FileUploadController.class);
        context.registerBean(StaticUploadController.class);
        try {
            context.refresh();
            var mvc = MockMvcBuilders.webAppContextSetup(context).build();
            status(mvc.perform(f.request("GET", "/music-resources/42/file", 0)).andReturn(), 401);
            status(mvc.perform(f.request("GET", "/file/download/9", 0)).andReturn(), 401);
            status(mvc.perform(f.request("GET", "/file/download/9", 1)).andReturn(), 200);
            status(mvc.perform(f.request("GET", "/uploads/track.mp3", 1)).andReturn(), 404);
            javax.imageio.ImageIO.write(new BufferedImage(1,1,BufferedImage.TYPE_INT_RGB), "png",
                    f.directory.resolve("avatar.png").toFile());
            when(f.users.count(any(Wrapper.class))).thenReturn(1L);
            status(mvc.perform(f.request("GET", "/uploads/avatar.png", 0)).andReturn(), 200);
        } finally { context.close(); }
    }
    @Test void zipExportCannotIncludeRejectedOrDeletedBytes() throws Exception {
        Fixture f = new Fixture();
        Page<MusicResources> page = new Page<>(); page.setRecords(List.of(f.record));
        when(f.music.getMusicResourceList(null,null,null,null,true,1,1000,null,null,null,"uploadTime","desc",null,null,null,null)).thenReturn(page);
        f.record.setApprovalStatus("rejected");
        var response = f.perform("/music-resources/export-music-files", 1);
        status(response, 200);
        try (var zip = new ZipInputStream(new ByteArrayInputStream(response.getResponse().getContentAsByteArray()))) {
            assertNull(zip.getNextEntry());
        }
        f.record.setApprovalStatus("pending");
        response = f.perform("/music-resources/export-music-files", 1);
        status(response, 200);
        try (var zip = new ZipInputStream(new ByteArrayInputStream(response.getResponse().getContentAsByteArray()))) {
            assertNotNull(zip.getNextEntry()); assertArrayEquals(audio, zip.readAllBytes());
        }
        f.owner.setIsLocked(true);
        status(f.perform("/music-resources/export-music-files", 1), 403);
    }
}
