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

    private JsonNode landmarksData;
    private final ObjectMapper mapper = new ObjectMapper();
    
    private static final Set<String> FILLER_WORDS = new HashSet<>(Arrays.asList(
        "is", "am", "are", "the", "a", "an", "was", "were", "to", "of", "will", "has", "have", "been", "can", "could", "should", "would", "with", "at", "in", "on", "from", "for"
    ));

    @PostConstruct
    public void init() throws IOException {
        System.out.println("Loading landmarks data...");
        ClassPathResource resource = new ClassPathResource("static_data/landmarks.json");
        landmarksData = mapper.readTree(resource.getInputStream());
        System.out.println("Landmarks data loaded.");
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
    public JsonNode getLandmarks(@PathVariable String lang, @PathVariable String word) {
        JsonNode langData = landmarksData.get(lang.toUpperCase());
        if (langData != null) {
            JsonNode wordData = langData.get(word.toLowerCase());
            if (wordData != null) {
                return wordData;
            }
        }
        return mapper.createArrayNode();
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
