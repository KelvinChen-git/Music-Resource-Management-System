package com.taffy.music.service;

import com.taffy.music.domain.MusicResources;
import com.taffy.music.repositories.MusicResourceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class MusicService {

    private final MusicResourceRepository musicResourcesRepository;

    public MusicService(MusicResourceRepository musicResourcesRepository) {
        this.musicResourcesRepository = musicResourcesRepository;
    }

    // 获取所有音乐资源
    public List<MusicResources> getAllMusic() {
        return musicResourcesRepository.findAll();
    }

    // 删除音乐资源
    @Transactional
    public void deleteMusic(Long musicID) {
        musicResourcesRepository.deleteById(musicID);
    }

    // 获取按歌曲名称首字母排序的音乐列表
    public List<MusicResources> getAllMusicSortedByTitle() {
        return musicResourcesRepository.findAll()
                .stream()
                .sorted((a, b) -> a.getTitle().compareToIgnoreCase(b.getTitle()))
                .collect(Collectors.toList());
    }

    // 获取按歌手名称首字母排序的音乐列表
    public List<MusicResources> getAllMusicSortedByArtist() {
        return musicResourcesRepository.findAll()
                .stream()
                .sorted((a, b) -> a.getArtist().compareToIgnoreCase(b.getArtist()))
                .collect(Collectors.toList());
    }

    // 获取按类别分类的音乐列表
    public List<MusicResources> getMusicByCategory(Integer categoryId) {
        if (categoryId == null) {
            return getAllMusic();
        }
        return musicResourcesRepository.findAll()
                .stream()
                .filter(music -> music.getCategoryid() != null && 
                        music.getCategoryid().equals(categoryId.longValue()))
                .collect(Collectors.toList());
    }

    // 根据歌曲名称或歌手名称搜索音乐
    public List<MusicResources> searchMusic(String keyword) {
        return musicResourcesRepository.findAll()
            .stream()
            .filter(music ->
                music.getApprovalStatus() != null &&
                (music.getTitle().toLowerCase().contains(keyword.toLowerCase()) ||
                 music.getArtist().toLowerCase().contains(keyword.toLowerCase()) ||
                 music.getAlbum().toLowerCase().contains(keyword.toLowerCase()))
            )
            .collect(Collectors.toList());
    }
    
}
