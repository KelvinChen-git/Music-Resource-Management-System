package com.taffy.music.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taffy.music.domain.MusicTags;
import org.apache.ibatis.annotations.Mapper;


@Mapper
public interface MusicTagMapper extends BaseMapper<MusicTags> {
} 