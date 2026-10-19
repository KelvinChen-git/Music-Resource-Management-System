package com.taffy.music.controller;

import com.taffy.music.annotation.Anonymous;
import com.taffy.music.service.MediaAccessService;
import com.taffy.music.utils.MediaResponses;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Path;
import java.util.Locale;

@RestController
public class StaticUploadController {
    private final MediaAccessService access;

    public StaticUploadController(MediaAccessService access) { this.access = access; }

    @Anonymous
    @GetMapping("/uploads/{*path}")
    public ResponseEntity<Resource> avatar(@PathVariable String path) {
        String relative = path.startsWith("/") ? path.substring(1) : path;
        Path avatar = access.publicAvatar(relative);
        if (avatar != null) {
            String lower = relative.toLowerCase(Locale.ROOT);
            MediaType type = lower.endsWith(".png") ? MediaType.IMAGE_PNG
                    : lower.endsWith(".gif") ? MediaType.IMAGE_GIF : MediaType.IMAGE_JPEG;
            return MediaResponses.file(avatar, avatar.getFileName().toString(), type, false);
        }
        access.requireViewer();
        throw MediaAccessService.unavailable(); // private music never falls back to filesystem serving
    }
}
