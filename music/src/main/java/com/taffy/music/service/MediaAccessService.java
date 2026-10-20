package com.taffy.music.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.taffy.music.config.UploadProperties;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.utils.UserContext;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/** A single current-database policy for all binary music entry points. */
@Service
public class MediaAccessService {
    private final MusicResourceService music;
    private final FileUploadService uploads;
    private final UserService users;
    private final UploadProperties properties;

    public MediaAccessService(MusicResourceService music, FileUploadService uploads,
                              UserService users, UploadProperties properties) {
        this.music = music;
        this.uploads = uploads;
        this.users = users;
        this.properties = properties;
    }

    public Users requireViewer() {
        Long id = UserContext.getCurrentUserId();
        if (id == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        Users viewer = users.getById(id);
        if (viewer == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号不可用");
        if (!Boolean.FALSE.equals(viewer.getIsLocked()))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "账号不可用");
        return viewer;
    }

    public static boolean canRead(MusicResources record, Users viewer) {
        if (record == null || !Boolean.FALSE.equals(record.getIsDeleted())) return false;
        String status = record.getApprovalStatus();
        if (!List.of("approved", "pending", "rejected").contains(status == null ? "" : status)) return false;
        return "ADMIN".equals(viewer.getRole()) || "approved".equals(status)
                || ("pending".equals(status) && viewer.getUserid().equals(record.getUserid()));
    }

    public MusicResources requireMusic(Long id) {
        Users viewer = requireViewer();
        MusicResources record = music.getById(id);
        if (!canRead(record, viewer)) throw unavailable();
        return record;
    }

    public FileUpload requireUpload(Long id) {
        Users viewer = requireViewer();
        FileUpload upload = uploads.getById(id);
        if (upload == null || !Integer.valueOf(1).equals(upload.getStatus())
                || !Boolean.FALSE.equals(upload.getDeleted())) throw unavailable();
        List<MusicResources> references = music.list(new LambdaQueryWrapper<MusicResources>()
                .eq(MusicResources::getFilePath, upload.getFilePath()));
        boolean permitted = references.isEmpty() ? upload.getOwnerUserId() != null
                && upload.getOwnerUserId().equals(viewer.getUserid())
                : references.stream().anyMatch(record -> canRead(record, viewer));
        if (!permitted) throw unavailable();
        return upload;
    }

    public Path requirePath(String relative) {
        try {
            if (relative == null || relative.isBlank() || relative.contains("\\")) throw unavailable();
            Path supplied = Path.of(relative);
            if (supplied.isAbsolute()) throw unavailable();
            for (Path segment : supplied) {
                if (segment.toString().equals("..") || segment.toString().equals(".")) throw unavailable();
            }
            Path root = Path.of(properties.getPath()).toRealPath();
            Path file = root.resolve(supplied).toRealPath();
            if (!file.startsWith(root) || !Files.isRegularFile(file)) throw unavailable();
            return file;
        } catch (IOException | java.nio.file.InvalidPathException e) {
            throw unavailable();
        }
    }

    /** Only registered, bounded raster avatars are public; no general upload access. */
    public Path publicAvatar(String relative) {
        String lower = relative.toLowerCase(Locale.ROOT);
        if (!(lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".png") || lower.endsWith(".gif")))
            return null;
        if (music.count(new LambdaQueryWrapper<MusicResources>().eq(MusicResources::getFilePath, relative)) != 0
                || users.count(new LambdaQueryWrapper<Users>().eq(Users::getAvatar, relative)) == 0) return null;
        Path path = requirePath(relative);
        try {
            String canonical = Path.of(properties.getPath()).toRealPath().relativize(path).toString()
                    .replace(java.io.File.separatorChar, '/');
            if (!relative.equals(canonical)) return null; // duplicate separators and symlink aliases cannot hide music references

            if (Files.size(path) > 5 * 1024 * 1024) return null;
            try (var stream = javax.imageio.ImageIO.createImageInputStream(path.toFile())) {
                if (stream == null) return null;
                var readers = javax.imageio.ImageIO.getImageReaders(stream);
                if (!readers.hasNext()) return null;
                var reader = readers.next();
                try {
                    reader.setInput(stream);
                    String format = reader.getFormatName().toLowerCase(Locale.ROOT);
                    boolean matches = (format.equals("jpeg") && (lower.endsWith(".jpg") || lower.endsWith(".jpeg")))
                            || (format.equals("png") && lower.endsWith(".png"))
                            || (format.equals("gif") && lower.endsWith(".gif"));
                    return matches && reader.getWidth(0) > 0 && reader.getHeight(0) > 0 ? path : null;
                } finally { reader.dispose(); }
            }
        } catch (IOException e) { return null; }
    }

    public static ResponseStatusException unavailable() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "资源不可用");
    }
}
