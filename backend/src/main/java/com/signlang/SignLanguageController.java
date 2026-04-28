package com.signlang;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/sign")
@CrossOrigin(origins = "*")
public class SignLanguageController {

    private volatile JsonNode landmarksData;
    private final ObjectMapper mapper = new ObjectMapper();
    
    private static final Set<String> FILLER_WORDS = new HashSet<>(Arrays.asList(
        "is", "am", "are", "the", "a", "an", "was", "were", "to", "of", "will", "has", "have", "been", "can", "could", "should", "would", "with", "at", "in", "on", "from", "for"
    ));

    @PostConstruct
    public void init() {
        new Thread(() -> {
            try {
                System.out.println("DEBUG: Starting landmarks data load. Current memory: " + (Runtime.getRuntime().totalMemory() / 1024 / 1024) + "MB");
                ClassPathResource resource = new ClassPathResource("static_data/landmarks.json");
                try (var is = resource.getInputStream()) {
                    landmarksData = mapper.readTree(is);
                }
                System.out.println("DEBUG: Landmarks data loaded successfully. Memory after load: " + (Runtime.getRuntime().totalMemory() / 1024 / 1024) + "MB");
                System.gc(); // Suggest GC to clean up temporary parsing objects
            } catch (Exception e) {
                System.err.println("CRITICAL ERROR loading landmarks data: " + e.getMessage());
                e.printStackTrace();
            }
        }).start();
    }

    @PostMapping("/transform")
    public List<String> transform(@RequestBody Map<String, String> request) {
        String sentence = request.getOrDefault("sentence", "");
        String[] words = sentence.toLowerCase().replace("?", "").split("\\s+");
        
        return Arrays.stream(words)
                .filter(w -> !FILLER_WORDS.contains(w))
                .map(this::normalizeWord)
                .collect(Collectors.toList());
    }

    @GetMapping("/landmarks/{lang}/{word}")
    public Object getLandmarks(@PathVariable String lang, @PathVariable String word) {
        if (landmarksData == null) {
            Map<String, String> error = new HashMap<>();
            error.put("status", "loading");
            error.put("message", "System is still initializing data. Please try again in a few seconds.");
            return org.springframework.http.ResponseEntity.status(503).body(error);
        }
        
        JsonNode langData = landmarksData.get(lang.toUpperCase());
        if (langData == null) {
            Map<String, String> error = new HashMap<>();
            error.put("message", "Language not supported: " + lang);
            return org.springframework.http.ResponseEntity.status(404).body(error);
        }

        JsonNode wordData = langData.get(word.toLowerCase());
        if (wordData == null) {
            Map<String, String> error = new HashMap<>();
            error.put("message", "Sign not found for word: " + word);
            return org.springframework.http.ResponseEntity.status(404).body(error);
        }

        return wordData;
    }

    private String normalizeWord(String word) {
        // Simple lemmatization placeholder
        // In a real app, use Stanford CoreNLP or OpenNLP
        if (word.endsWith("ing")) return word.substring(0, word.length() - 3);
        if (word.endsWith("s") && !word.endsWith("ss")) return word.substring(0, word.length() - 1);
        if (word.endsWith("ed")) return word.substring(0, word.length() - 2);
        return word;
    }
}
