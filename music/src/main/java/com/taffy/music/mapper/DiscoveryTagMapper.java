package com.taffy.music.mapper;

import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface DiscoveryTagMapper {
    @Select("<script>SELECT musicid FROM music_resource_tags WHERE tagid IN " +
            "<foreach item='tag' collection='tags' open='(' separator=',' close=')'>#{tag}</foreach> " +
            "GROUP BY musicid <if test='all'>HAVING COUNT(DISTINCT tagid)=#{count}</if></script>")
    List<Long> matching(@Param("tags") List<Long> tags, @Param("all") boolean all, @Param("count") int count);
}
