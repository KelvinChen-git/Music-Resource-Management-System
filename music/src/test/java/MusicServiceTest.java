import com.taffy.music.domain.MusicResources;
import com.taffy.music.repositories.MusicResourceRepository;
import com.taffy.music.service.MusicService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MusicServiceTest {

    @Mock
    private MusicResourceRepository musicResourceRepository;

    
    private MusicService musicService;

    private MusicResources music1;
    private MusicResources music2;
    private MusicResources music3;

    @BeforeEach
    void setUp() {
        // 初始化测试数据
        music1 = createTestMusic(1L, "Bohemian Rhapsody", "Queen", "A Night at the Opera", 1L);
        music1.setApprovalStatus("APPROVED"); // 新增此行

        music2 = createTestMusic(2L, "Hotel California", "Eagles", "Hotel California", 2L);
        music2.setApprovalStatus("APPROVED"); // 新增此行

        music3 = createTestMusic(3L, "Imagine", "John Lennon", "Imagine", 1L);
        music3.setApprovalStatus("APPROVED"); // 新增此行

    
        musicService = Mockito.spy(new MusicService(musicResourceRepository));
    }

    private MusicResources createTestMusic(Long id, String title, String artist, String album, Long categoryId) {
        MusicResources music = new MusicResources();
        music.setMusicid(id);
        music.setTitle(title);
        music.setArtist(artist);
        music.setAlbum(album);
        music.setCategoryid(categoryId);
        return music;
    }

    @Test
    void getAllMusic_ShouldReturnAllMusic() {
        // Arrange
        List<MusicResources> expectedMusic = Arrays.asList(music1, music2, music3);
        when(musicResourceRepository.findAll()).thenReturn(expectedMusic);

        // Act
        List<MusicResources> result = musicService.getAllMusic();

        // Assert
        assertEquals(3, result.size());
        assertTrue(result.containsAll(expectedMusic));
        verify(musicResourceRepository).findAll();
    }

    @Test
    void deleteMusic_ShouldCallRepositoryDelete() {
        // Arrange
        Long musicId = 1L;
        doNothing().when(musicResourceRepository).deleteById(musicId);

        // Act
        musicService.deleteMusic(musicId);

        // Assert
        verify(musicResourceRepository).deleteById(musicId);
    }

    @Test
    void getAllMusicSortedByTitle_ShouldReturnSortedList() {
        // Arrange
        List<MusicResources> unsorted = Arrays.asList(music3, music1, music2); // 故意乱序
        when(musicResourceRepository.findAll()).thenReturn(unsorted);

        // Act
        List<MusicResources> result = musicService.getAllMusicSortedByTitle();

        // Assert
        assertEquals(3, result.size());
        assertEquals("Bohemian Rhapsody", result.get(0).getTitle());
        assertEquals("Hotel California", result.get(1).getTitle());
        assertEquals("Imagine", result.get(2).getTitle());
    }

    @Test
    void getAllMusicSortedByArtist_ShouldReturnSortedList() {
        // Arrange
        List<MusicResources> unsorted = Arrays.asList(music1, music3, music2); // 故意乱序
        when(musicResourceRepository.findAll()).thenReturn(unsorted);

        // Act
        List<MusicResources> result = musicService.getAllMusicSortedByArtist();

        // Assert
        assertEquals(3, result.size());
        assertEquals("Eagles", result.get(0).getArtist());
        assertEquals("John Lennon", result.get(1).getArtist());
        assertEquals("Queen", result.get(2).getArtist());
    }

    @Test
    void getMusicByCategory_ShouldFilterByCategory() {
        // Arrange
        List<MusicResources> allMusic = Arrays.asList(music1, music2, music3);
        when(musicResourceRepository.findAll()).thenReturn(allMusic);

        // Act
        List<MusicResources> result = musicService.getMusicByCategory(1);

        // Assert
        assertEquals(2, result.size());
        assertTrue(result.stream().allMatch(m -> m.getCategoryid() == 1L));
        assertTrue(result.contains(music1));
        assertTrue(result.contains(music3));
    }

    @Test
    void getMusicByCategory_ShouldReturnAll_WhenCategoryIsNull() {
        // Arrange
        List<MusicResources> allMusic = Arrays.asList(music1, music2, music3);
        when(musicResourceRepository.findAll()).thenReturn(allMusic);

        // Act
        List<MusicResources> result = musicService.getMusicByCategory(null);

        // Assert
        assertEquals(3, result.size());
    }


    @Test
    void searchMusic_ShouldFindByTitleArtistOrAlbum() {
    // Arrange
    List<MusicResources> allMusic = Arrays.asList(music1, music2, music3);
    when(musicResourceRepository.findAll()).thenReturn(allMusic);

    // Act
    List<MusicResources> result1 = musicService.searchMusic("bohemian");
    List<MusicResources> result2 = musicService.searchMusic("eagles");
    List<MusicResources> result3 = musicService.searchMusic("night at");

    // 打印调试信息
    System.out.println("Result1: " + result1);
    System.out.println("Result2: " + result2);
    System.out.println("Result3: " + result3);

    // Assert
    assertEquals(1, result1.size());
    assertEquals("Bohemian Rhapsody", result1.get(0).getTitle());
    
    assertEquals(1, result2.size());
    assertEquals("Hotel California", result2.get(0).getTitle());
    
    assertEquals(1, result3.size());
    assertEquals("Bohemian Rhapsody", result3.get(0).getTitle());
}

    @Test
    void searchMusic_ShouldReturnEmpty_WhenNoMatch() {
        // Arrange
        List<MusicResources> allMusic = Arrays.asList(music1, music2, music3);
        when(musicResourceRepository.findAll()).thenReturn(allMusic);

        // Act
        List<MusicResources> result = musicService.searchMusic("Nonexistent");

        // Assert
        assertTrue(result.isEmpty());
    }

    // 演示@Spy的部分Mock用法
    @Test
    void getAllMusic_WithPartialMock() {
        // Arrange
        // 部分Mock：让repository返回空列表，但保留其他逻辑
        doReturn(Collections.emptyList()).when(musicResourceRepository).findAll();

        // Act
        List<MusicResources> result = musicService.getAllMusic();

        // Assert
        assertTrue(result.isEmpty());
        verify(musicResourceRepository).findAll();
    }
    
}