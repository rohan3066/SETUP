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
@RequestMapping("/api/signs")
@CrossOrigin(origins = "*")
public class SignLanguageController {

    private volatile JsonNode landmarksData;
    private final ObjectMapper mapper = new ObjectMapper();
    
    private static final Set<String> FILLER_WORDS = new HashSet<>(Arrays.asList(
        "is", "am", "are", "the", "a", "an", "was", "were", "to", "of", "will", "has", "have", "been", "can", "could", "should", "would", "with", "at", "in", "on", "from", "for",
        "i", "me", "my", "you", "your", "he", "him", "his", "she", "her", "it", "its", "we", "us", "our", "they", "them", "their"
    ));

    private static final Map<String, String> IRREGULAR_VERBS = new HashMap<>() {{
        put("am", "be"); put("is", "be"); put("are", "be"); put("was", "be"); put("were", "be");
        put("been", "be"); put("being", "be");
        put("went", "go"); put("gone", "go"); put("going", "go");
        put("ate", "eat"); put("eaten", "eat"); put("eating", "eat");
        put("saw", "see"); put("seen", "see"); put("seeing", "see");
        put("did", "do"); put("done", "do"); put("doing", "do");
        put("came", "come"); put("coming", "come");
        put("bought", "buy"); put("buying", "buy");
        put("took", "take"); put("taken", "take"); put("taking", "take");
        put("gave", "give"); put("given", "give"); put("giving", "give");
        put("felt", "feel"); put("feeling", "feel");
        put("knew", "know"); put("known", "know"); put("knowing", "know");
        put("thought", "think"); put("thinking", "think");
        put("told", "tell"); put("telling", "tell");
        put("said", "say"); put("saying", "say");
        put("worked", "work"); put("working", "work");
    }};

    @PostConstruct
    public void init() {
        new Thread(() -> {
            try {
                System.out.println("DEBUG: Starting landmarks data load. Current memory: " + (Runtime.getRuntime().totalMemory() / 1024 / 1024) + "MB");
                ClassPathResource resource = new ClassPathResource("static_data/landmarks.json");
                try (var is = resource.getInputStream()) {
                    landmarksData = mapper.readTree(is);
                }
                System.out.println("DEBUG: Landmarks data loaded successfully.");
                System.gc(); 
            } catch (Exception e) {
                System.err.println("CRITICAL ERROR loading landmarks data: " + e.getMessage());
                e.printStackTrace();
            }
        }).start();
    }

    @PostMapping("/transform")
    public List<String> transform(@RequestBody Map<String, String> request) {
        String sentence = request.getOrDefault("sentence", "");
        // Better tokenization: remove punctuation and split by whitespace
        String[] words = sentence.toLowerCase()
                .replaceAll("[^a-z\\s]", "")
                .split("\\s+");
        
        return Arrays.stream(words)
                .filter(w -> !w.isEmpty() && !FILLER_WORDS.contains(w))
                .map(this::normalizeWord)
                .collect(Collectors.toList());
    }

    @GetMapping("/landmarks/{lang}/{word}")
    public Object getLandmarks(@PathVariable String lang, @PathVariable String word) {
        if (landmarksData == null) {
            Map<String, String> error = new HashMap<>();
            error.put("status", "loading");
            error.put("message", "System is still initializing data.");
            return org.springframework.http.ResponseEntity.status(503).body(error);
        }
        
        JsonNode langData = landmarksData.get(lang.toUpperCase());
        if (langData == null) {
            return org.springframework.http.ResponseEntity.status(404).body(Collections.singletonMap("message", "Language not supported"));
        }

        String targetWord = word.toLowerCase();
        JsonNode wordData = langData.get(targetWord);
        
        // Fallback 1: Try normalized version if original word not found
        if (wordData == null) {
            String normalized = normalizeWord(targetWord);
            if (!normalized.equals(targetWord)) {
                wordData = langData.get(normalized);
            }
        }

        // Fallback 2: Basic suffix stripping if still not found
        if (wordData == null) {
            if (targetWord.endsWith("s")) wordData = langData.get(targetWord.substring(0, targetWord.length() - 1));
            if (wordData == null && targetWord.endsWith("ing")) wordData = langData.get(targetWord.substring(0, targetWord.length() - 3));
            if (wordData == null && targetWord.endsWith("ed")) wordData = langData.get(targetWord.substring(0, targetWord.length() - 2));
        }

        if (wordData == null) {
            return org.springframework.http.ResponseEntity.status(404).body(Collections.singletonMap("message", "Sign not found for: " + word));
        }

        return wordData;
    }

    private String normalizeWord(String word) {
        if (word == null || word.isEmpty()) return "";
        
        String w = word.toLowerCase().trim();
        
        // 1. Check irregular dictionary
        if (IRREGULAR_VERBS.containsKey(w)) {
            return IRREGULAR_VERBS.get(w);
        }
        
        // 2. Simple lemmatization
        if (w.endsWith("ing")) {
            if (w.length() > 5) return w.substring(0, w.length() - 3);
            return w;
        }
        if (w.endsWith("ed")) {
            if (w.length() > 4) return w.substring(0, w.length() - 2);
            return w;
        }
        if (w.endsWith("ies")) {
            if (w.length() > 3) return w.substring(0, w.length() - 3) + "y";
            return w;
        }
        if (w.endsWith("s") && !w.endsWith("ss")) {
            if (w.length() > 3) return w.substring(0, w.length() - 1);
            return w;
        }
        
        return w;
    }
}
