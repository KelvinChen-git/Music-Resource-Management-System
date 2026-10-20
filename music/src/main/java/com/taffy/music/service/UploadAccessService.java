package com.taffy.music.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.taffy.music.domain.FileUpload;
import com.taffy.music.domain.MusicResources;
import com.taffy.music.domain.Users;
import com.taffy.music.mapper.MusicResourceMapper;
import com.taffy.music.mapper.UserMapper;
import com.taffy.music.utils.UserContext;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Upload management is private to its persisted owner, including for administrators. */
@Service
public class UploadAccessService {
    private final FileUploadService uploads;
    private final UserMapper users;
    private final MusicResourceMapper music;

    public UploadAccessService(FileUploadService uploads, UserMapper users, MusicResourceMapper music) {
        this.uploads = uploads;
        this.users = users;
        this.music = music;
    }

    public Users requireViewer() {
        Long id = UserContext.getCurrentUserId();
        Users viewer = id == null ? null : users.selectById(id);
        if (viewer == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        if (!Boolean.FALSE.equals(viewer.getIsLocked()))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "账号不可用");
        return viewer;
    }

    public FileUpload requireOwned(Long id) {
        Users viewer = requireViewer();
        return requireOwned(uploads.getById(id), viewer);
    }

    public FileUpload requireOwned(FileUpload upload, Users viewer) {
        if (upload == null || !Boolean.FALSE.equals(upload.getDeleted())
                || upload.getOwnerUserId() == null || !upload.getOwnerUserId().equals(viewer.getUserid()))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不可用");
        return upload;
    }

    /** Caller must have an active transaction; ownership is checked on the locked current row. */
    public FileUpload requireOwnedLocked(Long id) {
        Users viewer = requireViewer();
        if (id == null || id <= 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不可用");
        FileUpload upload = uploads.getOne(new LambdaQueryWrapper<FileUpload>()
                .eq(FileUpload::getId, id).eq(FileUpload::getOwnerUserId, viewer.getUserid()).last("FOR UPDATE"));
        return requireOwned(upload, viewer);
    }

    public void requireUnreferenced(FileUpload upload) {
        // Locking reads see references committed while this transaction waited for the
        // upload lock; a repeatable-read snapshot could otherwise miss a new binding.
        if (!users.selectList(new LambdaQueryWrapper<Users>().select(Users::getUserid)
                .eq(Users::getAvatar, upload.getFilePath()).last("FOR UPDATE")).isEmpty()
                || !music.selectList(new LambdaQueryWrapper<MusicResources>().select(MusicResources::getMusicid)
                .eq(MusicResources::getFilePath, upload.getFilePath()).last("FOR UPDATE")).isEmpty())
            throw new ResponseStatusException(HttpStatus.CONFLICT, "文件已被音乐资源或头像引用，不能删除上传记录");
    }

    public void requireAvatar(String relative, Long targetUserId) {
        requireViewer();
        if (relative == null || !relative.toLowerCase(java.util.Locale.ROOT).matches(".*\\.(jpg|jpeg|png|gif)$"))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "头像文件不可用");
        FileUpload upload = uploads.getOne(new LambdaQueryWrapper<FileUpload>()
                .eq(FileUpload::getFilePath, relative).eq(FileUpload::getOwnerUserId, targetUserId)
                .eq(FileUpload::getStatus, 1).last("LIMIT 1 FOR UPDATE"));
        if (upload == null || !Boolean.FALSE.equals(upload.getDeleted())
                || !targetUserId.equals(upload.getOwnerUserId()) || !Integer.valueOf(1).equals(upload.getStatus()))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "头像文件不可用");
    }
}
