import React, { useState, useEffect, useCallback } from 'react';
import { Mic, Play, Settings, Video, Info, Activity, Volume2, Search } from 'lucide-react';
import AvatarCanvas from './components/AvatarCanvas';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api/sign";

function App() {
  const [inputText, setInputText] = useState("");
  const [currentPoints, setCurrentPoints] = useState(null);
  const [currentCaption, setCurrentCaption] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isPlaying, setIsPlaying] = useState(false);
  const [lang, setLang] = useState("ISL");
  const [isMuted, setIsMuted] = useState(false);

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
    setStatus("Analyzing...");
    
    try {
      // 1. Transform sentence to words
      const transformRes = await fetch(`${API_BASE}/transform`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence: inputText })
      });
      const words = await transformRes.json();
      
      const sequenceToPlay = [];
      for (const word of words) {
        try {
          const landmarkRes = await fetch(`${API_BASE}/landmarks/${lang}/${word}`);
          if (!landmarkRes.ok) continue;
          
          const text = await landmarkRes.text();
          if (!text) continue;
          
          const frames = JSON.parse(text);
          if (frames && frames.length > 0) {
            sequenceToPlay.push({ word, frames });
          } else {
            console.warn(`Word not found in ${lang} DB: ${word}`);
          }
        } catch (e) {
          console.error(`Error fetching word ${word}:`, e);
        }
      }

      if (sequenceToPlay.length === 0) {
        setStatus("No matching signs found");
        setIsPlaying(false);
        return;
      }

      setStatus(`Playing: ${sequenceToPlay.map(s => s.word).join(" ")}`);
      
      let lastFrame = null;
      for (const item of sequenceToPlay) {
        const { word, frames } = item;
        speak(word); // Vocalize word as it starts
        
        // Transition from last word if exists
        if (lastFrame) {
          await interpolateFrames(lastFrame, frames[0], word, 20);
        }

        for (let i = 0; i < frames.length - 1; i++) {
          await interpolateFrames(frames[i], frames[i+1], word, 4);
        }
        lastFrame = frames[frames.length - 1];
      }
    } catch (error) {
      console.error("Playback error:", error);
      setStatus("Error fetching data");
    } finally {
      setIsPlaying(false);
      setCurrentPoints(null);
      setCurrentCaption("");
      setStatus("Ready");
    }
  };

  const interpolateFrames = (frameA, frameB, word, steps) => {
    return new Promise((resolve) => {
      let currentStep = 0;
      const easeInOut = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      
      const step = () => {
        const t = easeInOut(currentStep / steps);
        const interpolated = frameA.map((pt, i) => {
          // Indices for hands are 33-74
          const isHand = i >= 33 && i <= 74;
          
          if (frameB[i][0] === 0 && frameB[i][1] === 0) {
            // If the target is missing hand data, but we have data in frameA, keep it.
            if (isHand && pt[0] !== 0) return [pt[0], pt[1]];
            return [pt[0], pt[1]];
          }
          
          if (pt[0] === 0 && pt[1] === 0) {
            return [frameB[i][0], frameB[i][1]];
          }
          
          return [
            pt[0] + (frameB[i][0] - pt[0]) * t,
            pt[1] + (frameB[i][1] - pt[1]) * t
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
          <div className="input-area" style={{ padding: '10px', color: 'var(--accent-color)', fontWeight: 'bold' }}>
            Indian Sign Language (ISL)
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
        <AvatarCanvas points={currentPoints} caption={currentCaption} />
        
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
