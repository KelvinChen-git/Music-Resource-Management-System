package com.taffy.music.controller;

import com.taffy.music.domain.MusicResources;
import com.taffy.music.service.MusicService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/music")
public class MusicController {

    private final MusicService musicService;

    public MusicController(MusicService musicService) {
        this.musicService = musicService;
    }

    // 获取所有音乐资源
    @GetMapping
    public ResponseEntity<Iterable<MusicResources>> getAllMusic() {
        return ResponseEntity.ok(musicService.getAllMusic());
    }

    // 按歌曲名称首字母排序
    @GetMapping("/sortByTitle")
    public ResponseEntity<List<MusicResources>> getMusicSortedByTitle() {
        return ResponseEntity.ok(musicService.getAllMusicSortedByTitle());
    }

    // 按歌手名称首字母排序
    @GetMapping("/sortByArtist")
    public ResponseEntity<List<MusicResources>> getMusicSortedByArtist() {
        return ResponseEntity.ok(musicService.getAllMusicSortedByArtist());
    }

    // 删除音乐资源
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteMusic(@PathVariable Long id) {
        musicService.deleteMusic(id);
        return ResponseEntity.noContent().build();
    }

    // 根据类别获取音乐资源
    @GetMapping("/category/{categoryId}")
    public ResponseEntity<List<MusicResources>> getMusicByCategory(@PathVariable(required = false) Integer categoryId) {
        if (categoryId == null) {
            return ResponseEntity.ok(musicService.getAllMusic());
        }
        return ResponseEntity.ok(musicService.getMusicByCategory(categoryId));
    }

    // 根据歌曲名称或歌手名称搜索音乐资源
    @GetMapping("/search")
    public ResponseEntity<List<MusicResources>> searchMusic(@RequestParam String keyword) {
        return ResponseEntity.ok(musicService.searchMusic(keyword));
    }
}
