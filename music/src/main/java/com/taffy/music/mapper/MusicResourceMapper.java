package com.taffy.music.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taffy.music.domain.MusicResources;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import java.util.List;
import java.util.Map;

@Mapper
public interface MusicResourceMapper extends BaseMapper<MusicResources> {

    @Delete("DELETE FROM music_resource_tags WHERE musicid = #{musicId}")
    void deleteTagsByMusicId(@Param("musicId") Long musicId);

    @Insert("INSERT INTO music_resource_tags (musicid, tagid) VALUES (#{musicId}, #{tagId})")
    void insertMusicTag(@Param("musicId") Long musicId, @Param("tagId") Long tagId);

    @Select("<script>" +
            "SELECT DISTINCT musicid FROM music_resource_tags WHERE tagid IN " +
            "<foreach item='item' collection='tagIds' open='(' separator=',' close=')'>" +
            "#{item}" +
            "</foreach>" +
            "</script>")
    List<Long> findMusicIdsByTagIds(@Param("tagIds") List<Long> tagIds);

    @Select("SELECT tagid FROM music_resource_tags WHERE musicid = #{musicId}")
    List<Long> findTagIdsByMusicId(@Param("musicId") Long musicId);

    /**
     * 使用复杂的过滤器和关键字进行分页查询
     * @param page 分页对象
     * @param params 包含所有过滤/排序/关键字参数的Map
     * @return 分页结果
     */
    Page<MusicResources> selectMusicPageWithComplexFilters(Page<MusicResources> page, @Param("params") Map<String, Object> params);
}