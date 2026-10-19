package com.taffy.music.domain;
import jakarta.persistence.*;
import lombok.Data;

import java.io.Serializable;

@Entity
@Table(name = "music_resource_tags")
@Data
@IdClass(MusicResourceTagId.class)
public class MusicResourceTags {
    @Id
    @ManyToOne
    @JoinColumn(name = "musicid")
    private MusicResources music;

    @Id
    @ManyToOne
    @JoinColumn(name = "tagid")
    private MusicTags tag;
}


