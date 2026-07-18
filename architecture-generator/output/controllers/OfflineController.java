package com.app.controllers;

import org.springframework.web.bind.annotation.*;

@RestController
public class OfflineController {

    
    
    
    @GetMapping("/offline/{userId}")
    
    public OfflineDTO handle() {
        return null;
    }
    
}