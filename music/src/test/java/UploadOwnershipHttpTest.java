import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.config.*;
import com.taffy.music.controller.*;
import com.taffy.music.domain.*;
import com.taffy.music.mapper.MusicResourceMapper;
import com.taffy.music.interceptor.JwtAuthenticationInterceptor;
import com.taffy.music.service.*;
import com.taffy.music.service.impl.MusicResourceServiceImpl;
import com.taffy.music.utils.*;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.*;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Stream;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

class UploadOwnershipHttpTest {
    @TempDir Path root;
    FileUploadService files;
    FileChunkService chunks;
    com.taffy.music.mapper.UserMapper users;
    MusicResourceMapper music;
    UploadAccessService access;
    FileUpload upload;
    Users owner, other, admin;
    JwtUtil jwt;
    MockMvc mvc;

    @BeforeEach void setup() {
        var assistant = new MapperBuilderAssistant(new MybatisConfiguration(), "ownership-test");
        TableInfoHelper.initTableInfo(assistant, FileUpload.class);
        TableInfoHelper.initTableInfo(assistant, MusicResources.class);
        TableInfoHelper.initTableInfo(assistant, Users.class);
        files = mock(FileUploadService.class); chunks = mock(FileChunkService.class);
        users = mock(com.taffy.music.mapper.UserMapper.class); music = mock(MusicResourceMapper.class);
        owner = user(1, "USER"); other = user(2, "USER"); admin = user(3, "ADMIN");
        when(users.selectById(1L)).thenReturn(owner); when(users.selectById(2L)).thenReturn(other);
        when(users.selectById(3L)).thenReturn(admin);
        upload = new FileUpload(); upload.setId(9L); upload.setOwnerUserId(1L); upload.setDeleted(false);
        upload.setStatus(0); upload.setFilePath("temp/fixture"); upload.setChunkCount(1); upload.setFileSize(3L);
        upload.setFileName("fixture.mp3");
        when(files.getById(9L)).thenReturn(upload);
        when(files.getOne(any(Wrapper.class))).thenReturn(upload);
        when(files.save(any())).thenReturn(true); when(files.removeById(9L)).thenReturn(true);
        access = new UploadAccessService(files, users, music);
        var properties = new UploadProperties(); properties.setPath(root.toString());
        properties.setTempPath(root.resolve("chunks").toString()); properties.setAllowedTypes("mp3");
        var controller = new FileUploadController();
        ReflectionTestUtils.setField(controller,"fileUploadService",files);
        ReflectionTestUtils.setField(controller,"fileChunkService",chunks);
        ReflectionTestUtils.setField(controller,"uploadProperties",properties);
        ReflectionTestUtils.setField(controller,"uploadAccessService",access);
        ReflectionTestUtils.setField(controller,"uploadIntegrityService",new UploadIntegrityService(files,chunks,properties,access));
        var metadata = new MusicResourceServiceImpl();
        ReflectionTestUtils.setField(metadata,"uploadAccessService",access);
        ReflectionTestUtils.setField(metadata,"baseMapper",music);
        var resource = new MusicResourceController();
        ReflectionTestUtils.setField(resource,"musicResourceService",metadata);
        jwt = new JwtUtil(); ReflectionTestUtils.setField(jwt,"secret","z".repeat(128));
        ReflectionTestUtils.setField(jwt,"expiration",60000L);
        var interceptor = new JwtAuthenticationInterceptor(); ReflectionTestUtils.setField(interceptor,"jwtUtil",jwt);
        var profileService = new com.taffy.music.service.impl.UserServiceImpl();
        ReflectionTestUtils.setField(profileService,"userMapper",users);
        ReflectionTestUtils.setField(profileService,"baseMapper",users);
        ReflectionTestUtils.setField(profileService,"uploadAccessService",access);
        var profile = new AuthController();ReflectionTestUtils.setField(profile,"userService",profileService);
        var legacy = new MusicController(new MusicService(mock(com.taffy.music.repositories.MusicResourceRepository.class)));
        ReflectionTestUtils.setField(legacy,"mediaAccessService",new MediaAccessService(
                mock(MusicResourceService.class),files,profileService,properties));
        var administration = new UserController(profileService,new com.fasterxml.jackson.databind.ObjectMapper());
        mvc = MockMvcBuilders.standaloneSetup(controller,resource,profile,legacy,administration).setControllerAdvice(new GlobalExceptionHandler())
                .addInterceptors(interceptor).build();
    }
    @AfterEach void clear() { UserContext.clear(); }
    Users user(long id,String role) { var u=new Users();u.setUserid(id);u.setRole(role);u.setIsLocked(false);return u; }
    MockHttpServletRequestBuilder auth(MockHttpServletRequestBuilder request,int viewer) {
        return viewer==0?request:request.header("Authorization","Bearer "+jwt.generateToken((long)viewer,"test@example.invalid"));
    }
    void status(MockHttpServletRequestBuilder request,int viewer,int expected) throws Exception {
        var response=mvc.perform(auth(request,viewer)).andReturn().getResponse();
        assertEquals(expected,response.getStatus(),response.getContentAsString());
    }
    MockHttpServletRequestBuilder action(String operation) {
        return switch(operation) {
            case "detail" -> get("/file/9");
            case "status" -> get("/file/status/9");
            case "missing" -> get("/file/missing-chunks?fileId=9");
            case "merge" -> post("/file/merge?fileId=9");
            case "delete" -> delete("/file/9");
            case "metadata" -> post("/music-resources/metadata?fileId=9").contentType("application/json").content("{\"title\":\"claim\"}");
            default -> multipart("/file/chunk").file(new MockMultipartFile("chunk","abc".getBytes()))
                    .param("fileId","9").param("chunkIndex","0").param("chunkMd5","900150983cd24fb0d6963f7d28e17f72");
        };
    }
    @TestFactory Stream<DynamicTest> strangersAndAdministratorsCannotManageOthersUploads() {
        return Stream.of(0,2,3).flatMap(viewer->Stream.of("detail","status","missing","chunk","merge","delete","metadata")
            .map(op->DynamicTest.dynamicTest(viewer+"/"+op,()->{
                status(action(op),viewer,viewer==0?401:404);
                verify(chunks,never()).save(any()); verify(files,never()).updateById(any());
                verify(files,never()).removeById(anyLong()); verify(music,never()).insert(any(MusicResources.class));
                try(var paths=Files.walk(root)){assertEquals(0,paths.filter(Files::isRegularFile).count());}
            })));
    }
    @TestFactory Stream<DynamicTest> legacyUnknownOwnerCannotBeClaimedOrMutated() {
        return Stream.of("detail","status","missing","chunk","merge","delete","metadata").map(op->DynamicTest.dynamicTest(op,()->{
            upload.setOwnerUserId(null);status(action(op),1,404);
            verify(chunks,never()).save(any());verify(files,never()).removeById(anyLong());
        }));
    }
    @Test void currentAccountIsRecheckedForEveryManagementEntry() throws Exception {
        for(String op:List.of("detail","status","missing","chunk","merge","delete","metadata")) {
            owner.setIsLocked(true);status(action(op),1,403);
            when(users.selectById(1L)).thenReturn(null);status(action(op),1,401);
            when(users.selectById(1L)).thenReturn(owner);
        }
    }
    @Test void creationTakesOwnerFromDatabaseIdentity() throws Exception {
        status(post("/file/create").contentType("application/json").content("{\"fileName\":\"f.mp3\",\"fileSize\":3,\"chunkCount\":1,\"fileMd5\":\"900150983cd24fb0d6963f7d28e17f72\",\"ownerUserId\":2}"),1,200);
        verify(files).save(argThat(f->Long.valueOf(1L).equals(f.getOwnerUserId())));
    }
    @Test void ordinaryUploadAlsoPersistsServerOwner() throws Exception {
        status(multipart("/file/upload").file(new MockMultipartFile("file","f.mp3","audio/mpeg","abc".getBytes())),1,200);
        verify(files).save(argThat(f->Long.valueOf(1L).equals(f.getOwnerUserId()) && f.getStatus()==1));
    }
    @Test void failedOrdinaryUploadPersistenceRemovesCandidate() throws Exception {
        when(files.save(any())).thenReturn(false);
        mvc.perform(auth(multipart("/file/upload").file(new MockMultipartFile("file","f.mp3","audio/mpeg","abc".getBytes())),1));
        try(var paths=Files.walk(root)){assertEquals(0,paths.filter(Files::isRegularFile).count());}
    }
    @Test void ownStatusAndDetailRemainAvailable() throws Exception {
        status(get("/file/9"),1,200);status(get("/file/status/9"),1,200);
        status(get("/file/missing-chunks?fileId=9"),1,200);
    }
    @Test void deletingUnreferencedUploadOnlyTombstonesDatabase() throws Exception {
        Path bytes=Files.writeString(root.resolve("retained.mp3"),"abc");upload.setFilePath(bytes.toString());
        status(delete("/file/9"),1,200);assertTrue(Files.exists(bytes));verify(files).removeById(9L);
        verify(chunks,never()).remove(any(Wrapper.class));
    }
    @Test void anyMusicReferenceBlocksDeletionIncludingRecoverableRecords() throws Exception {
        when(music.selectList(any(Wrapper.class))).thenReturn(List.of(new MusicResources()));
        status(delete("/file/9"),1,409);verify(files,never()).removeById(anyLong());
    }
    @Test void listsAreOwnerScopedAndSortColumnIsWhitelisted() throws Exception {
        when(files.page(any(Page.class),any(Wrapper.class))).thenReturn(new Page<FileUpload>());
        status(get("/file/list?orderBy=id%20desc,(select%20sleep(5))"),1,200);
        verify(files).page(any(Page.class),argThat((Wrapper<FileUpload> w)->{
            assertTrue(w.getSqlSegment().contains("owner_user_id"));
            assertFalse(w.getSqlSegment().contains("sleep"));return true;
        }));
    }

    @Test void avatarCannotPublishAnotherOwnersPrivateImage() throws Exception {
        upload.setStatus(1);upload.setFilePath("private.png");upload.setOwnerUserId(2L);
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"private.png\"}"),1,404);
        verify(users,never()).update(isNull(),any(Wrapper.class));
    }
    @Test void avatarCannotClaimLegacyOrIncompleteImage() throws Exception {
        upload.setStatus(1);upload.setFilePath("legacy.png");upload.setOwnerUserId(null);
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"legacy.png\"}"),1,404);
        upload.setOwnerUserId(1L);upload.setStatus(0);
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"legacy.png\"}"),1,404);
        verify(users,never()).update(isNull(),any(Wrapper.class));
    }
    @Test void ownCompleteImageCanBecomeAvatarAndThenCannotBeDeleted() throws Exception {
        upload.setStatus(1);upload.setFilePath("owned.png");
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"owned.png\"}"),1,200);
        verify(users).update(isNull(),argThat((Wrapper<Users> w)-> {
            String sql=((com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<Users>)w).getSqlSet();
            assertTrue(sql.contains("avatar"));assertFalse(sql.contains("role"));assertFalse(sql.contains("is_locked"));return true;
        }));
        when(users.selectList(any(Wrapper.class))).thenReturn(List.of(owner));
        status(delete("/file/9"),1,409);verify(files,never()).removeById(anyLong());
    }
    @Test void musicCannotBecomeAvatarAndLockedAccountCannotRegisterNewAvatar() throws Exception {
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"track.mp3\"}"),1,404);
        owner.setIsLocked(true);
        status(put("/auth/profile").contentType("application/json").content("{\"avatar\":\"owned.png\"}"),1,403);
    }

    @TestFactory Stream<DynamicTest> legacyDeletionIsUnavailableToEveryIdentity() {
        return Stream.of(0,1,2,3).map(viewer->DynamicTest.dynamicTest("legacy delete/viewer="+viewer,()-> {
            status(delete("/music/42"),viewer,viewer==0?401:410);
            verify(files,never()).removeById(anyLong());
        }));
    }
    @Test void legacyDeleteRechecksLockedAndRemovedAccounts() throws Exception {
        owner.setIsLocked(true);status(delete("/music/42"),1,403);
        when(users.selectById(1L)).thenReturn(null);status(delete("/music/42"),1,401);
    }
    @Test void administratorCannotCreateNewUserWithAnyExistingAvatar() throws Exception {
        status(post("/users").contentType("application/json")
                .content("{\"name\":\"fixture\",\"email\":\"new@example.invalid\",\"avatar\":\"private.png\"}"),3,400);
        verify(users,never()).insert(any(Users.class));
    }
    @Test void administratorCreationRechecksCurrentLock() throws Exception {
        admin.setIsLocked(true);
        status(post("/users").contentType("application/json").content("{\"name\":\"fixture\"}"),3,403);
        verify(users,never()).insert(any(Users.class));
    }
    @Test void blankAvatarOnNewUserIsNormalizedToNull() throws Exception {
        status(post("/users").contentType("application/json")
                .content("{\"name\":\"fixture\",\"avatar\":\"  \"}"),3,200);
        verify(users).insert(argThat((Users u)->u.getAvatar()==null));
    }
    @Test void profileWritesOnlyEditableFieldsEvenWhenSnapshotContainsSecurityState() throws Exception {
        owner.setRole("ADMIN");owner.setIsLocked(false);owner.setPassword("synthetic-hash");
        status(put("/auth/profile").contentType("application/json").content("{\"name\":\"new name\"}"),1,200);
        verify(users).update(isNull(),argThat((Wrapper<Users> w)-> {
            String sql=((com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<Users>)w).getSqlSet();
            assertTrue(sql.contains("name"));assertFalse(sql.contains("role"));
            assertFalse(sql.contains("is_locked"));assertFalse(sql.contains("password"));return true;
        }));
        verify(users,never()).updateById(any(Users.class));
    }
}
