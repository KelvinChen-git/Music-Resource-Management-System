package com.taffy.music.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

/** Fields accepted by the existing administrator edit endpoint. */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AdminUpdateUserDTO {
    private String name;
    private String email;
    private String avatar;
    private String role;
}
