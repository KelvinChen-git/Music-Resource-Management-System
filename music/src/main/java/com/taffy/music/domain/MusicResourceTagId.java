package com.taffy.music.domain;

import lombok.Data;

import java.io.Serializable;

@Data
public class MusicResourceTagId implements Serializable {
    private Long music;
    private Long tag;
}
