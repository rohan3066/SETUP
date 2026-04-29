import React, { useState, useEffect, useCallback } from 'react';
import { Mic, Play, Settings, Video, Info, Activity, Volume2, Search, Languages, Globe } from 'lucide-react';
import AvatarCanvas from './components/AvatarCanvas';
import { motion, AnimatePresence } from 'framer-motion';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api/signs";
if (API_BASE.endsWith("/api/sign")) {
  API_BASE += "s";
}

function App() {
  const [inputText, setInputText] = useState("");
  const [currentPoints, setCurrentPoints] = useState(null);
  const [currentCaption, setCurrentCaption] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lang, setLang] = useState("ISL");
  const [isMuted, setIsMuted] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('app-theme') || 'default');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const speak = (text) => {
    if (isMuted) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
  };

  const playSequence = async () => {
    if (!inputText || isPlaying) return;

    setIsPlaying(true);
    setIsLoading(true);
    setStatus("Analyzing...");

    try {
      // 1. Transform sentence to words
      const transformRes = await fetch(`${API_BASE}/transform`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence: inputText })
      });
      
      if (!transformRes.ok) {
        throw new Error(`Server returned ${transformRes.status}: ${transformRes.statusText}`);
      }

      const words = await transformRes.json();
      setIsLoading(false);
      
      if (!Array.isArray(words)) {
        throw new Error("Invalid response format from server");
      }

      const sequenceToPlay = [];
      const missingWords = [];

      for (const word of words) {
        try {
          const landmarkRes = await fetch(`${API_BASE}/landmarks/${lang}/${word}`);
          if (!landmarkRes.ok) {
            missingWords.push(word);
            continue;
          }

          const text = await landmarkRes.text();
          const data = JSON.parse(text);
          if (data.status === "loading") {
            setStatus("Server still loading data...");
            setIsPlaying(false);
            return;
          }

          if (Array.isArray(data) && data.length > 0) {
            sequenceToPlay.push({ word, frames: data });
          } else {
            missingWords.push(word);
            console.warn(`Word not found in ${lang} DB: ${word}`);
          }
        } catch (e) {
          console.error(`Error fetching word ${word}:`, e);
          missingWords.push(word);
        }
      }

      if (sequenceToPlay.length === 0) {
        setStatus(`Signs not found: ${missingWords.join(", ")}`);
        setIsPlaying(false);
        return;
      }

      if (missingWords.length > 0) {
        setStatus(`Missing: ${missingWords.join(", ")}. Playing others...`);
        await new Promise(r => setTimeout(r, 2000)); // Show missing info for 2s
      }

      setStatus(`Playing: ${sequenceToPlay.map(s => s.word).join(" ")}`);

      let lastFrame = null;
      for (const item of sequenceToPlay) {
        const { word, frames } = item;
        speak(word); // Vocalize word as it starts

        // Transition from last word if exists
        if (lastFrame) {
          await interpolateFrames(lastFrame, frames[0], word, 30); // Slower transition between words
        }

        for (let i = 0; i < frames.length - 1; i++) {
          await interpolateFrames(frames[i], frames[i + 1], word, 6); // Smoother intra-word frames
        }
        lastFrame = frames[frames.length - 1];
      }
    } catch (error) {
      console.error("Playback error:", error);
      if (error.message.includes("Failed to fetch")) {
        setStatus("Network Error: Cannot reach server");
      } else {
        setStatus("Error: " + error.message);
      }
    } finally {
      setIsPlaying(false);
      setIsLoading(false);
      setCurrentPoints(null);
      setCurrentCaption("");
      // Keep the error message visible for 5 seconds
      setTimeout(() => setStatus(prev => (prev.includes("Error") || prev.includes("...") ? prev : "Ready")), 5000);
      setTimeout(() => setStatus("Ready"), 8000);
    }
  };

  const interpolateFrames = (frameA, frameB, word, steps) => {
    return new Promise((resolve) => {
      let currentStep = 0;
      const easeInOut = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

      const step = () => {
        const t = easeInOut(currentStep / steps);
        const interpolated = frameA.map((pt, i) => {
          const isHand = i >= 33 && i <= 74;
          const target = frameB[i];

          // If target point is missing (0,0), handle based on type
          if (target[0] === 0 && target[1] === 0) {
            if (isHand) {
              // For hands, if target is missing, fade them towards the wrist or keep last position
              // This prevents hands from disappearing instantly
              return [pt[0], pt[1]];
            }
            return [pt[0], pt[1]];
          }

          // If starting point was missing, snap to target or interpolate from a neutral pose
          if (pt[0] === 0 && pt[1] === 0) {
            return [target[0], target[1]];
          }

          // Enhanced smoothing for fingers (isHand)
          // We can use a different easing or just standard linear interpolation with higher step count
          return [
            pt[0] + (target[0] - pt[0]) * t,
            pt[1] + (target[1] - pt[1]) * t
          ];
        });

        setCurrentPoints(interpolated);
        setCurrentCaption(word);

        currentStep++;
        if (currentStep <= steps) {
          requestAnimationFrame(step);
        } else {
          resolve();
        }
      };

      requestAnimationFrame(step);
    });
  };

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.onstart = () => setStatus("Listening...");
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInputText(transcript);
      setStatus("Voice captured");
    };
    recognition.onerror = () => setStatus("Speech error");
    recognition.onend = () => setStatus("Ready");

    recognition.start();
  };

  return (
    <div className="dashboard">
      {/* Sidebar Controls */}
      <div className="sidebar glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
          <Activity className="accent-text" size={28} />
          <h2 style={{ fontSize: '1.5rem', fontWeight: '800' }}>Sign<span className="accent-text">System</span></h2>
        </div>

        <div className="status-badge">
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: status === 'Ready' ? '#44d07d' : '#ffb300' }} />
          <span style={{ color: 'var(--text-muted)' }}>{status}</span>
        </div>

        <div style={{ marginTop: '20px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '8px', fontSize: '0.9rem' }}>Sign Model</label>
          <div className="language-selector">
            <button 
              className={`lang-btn ${lang === 'ISL' ? 'active' : ''}`}
              onClick={() => setLang('ISL')}
            >
              <Globe size={14} style={{ marginRight: '6px' }} />
              ISL
            </button>
            <button 
              className={`lang-btn ${lang === 'ASL' ? 'active' : ''}`}
              onClick={() => setLang('ASL')}
            >
              <Languages size={14} style={{ marginRight: '6px' }} />
              ASL
            </button>
          </div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '8px', fontSize: '0.9rem' }}>Appearance</label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
            {['default', 'midnight', 'light', 'cyber'].map((t) => (
              <button
                key={t}
                onClick={() => setTheme(t)}
                className="theme-btn"
                style={{
                  padding: '10px 5px',
                  borderRadius: '12px',
                  border: theme === t ? '2px solid var(--accent-color)' : '1px solid var(--panel-border)',
                  background: theme === t ? 'rgba(255,255,255,0.05)' : 'transparent',
                  color: theme === t ? 'var(--accent-color)' : 'var(--text-muted)',
                  fontSize: '0.65rem',
                  textTransform: 'uppercase',
                  fontWeight: '800',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  letterSpacing: '1px'
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, marginTop: '20px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '8px', fontSize: '0.9rem' }}>Input Sentence</label>
          <textarea
            className="input-area"
            placeholder="Type here or use voice..."
            rows={5}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '15px' }}>
            <button className="neon-btn secondary" onClick={startListening} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <Mic size={18} /> SPEECH
            </button>
            <button className="neon-btn" onClick={playSequence} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <Play size={18} /> {isPlaying ? "PLAYING" : "PLAY"}
            </button>
          </div>
        </div>

        <div style={{ padding: '15px', borderTop: '1px solid var(--panel-border)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Info size={14} />
            <span>Try "nurse works at hospital"</span>
          </div>
        </div>
      </div>

      {/* Main Avatar View */}
      <div className="main-view glass-panel">
        {isLoading && (
          <div className="loader-overlay">
            <div className="spinner"></div>
            <div className="loading-text">Analyzing Signs...</div>
          </div>
        )}
        <AvatarCanvas points={currentPoints} caption={currentCaption} />
        
        <div className="language-badge">
          {lang === 'ISL' ? 'Indian Sign Language' : 'American Sign Language'}
        </div>

        {/* Overlays */}
        <div style={{ position: 'absolute', top: 20, right: 20, display: 'flex', gap: '10px' }}>
          <button className="glass-panel" style={{ padding: '10px', borderRadius: '12px' }}><Video size={20} /></button>
          <button className="glass-panel" style={{ padding: '10px', borderRadius: '12px' }}><Settings size={20} /></button>
        </div>
      </div>

      {/* Bottom Stats/Sequence Panel */}
      <div className="bottom-panel glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <div className="accent-text"><Search size={24} /></div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recognition Result</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>IDLE</div>
          </div>
        </div>
        <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: isPlaying ? '100%' : 0 }}
            transition={{ duration: 2 }}
            style={{ height: '100%', background: 'var(--accent-color)' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setIsMuted(!isMuted)}
            className="glass-panel"
            style={{ padding: '8px', borderRadius: '10px', color: isMuted ? '#ff5252' : 'var(--accent-color)' }}
          >
            {isMuted ? <Volume2 size={20} style={{ opacity: 0.5 }} /> : <Volume2 size={20} />}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
