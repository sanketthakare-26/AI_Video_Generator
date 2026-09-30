import React, { useState, useRef, useEffect } from 'react';
import { Mic, Volume2, Loader2, AlertTriangle, CheckCircle, Clock, Music, Hourglass } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VoiceGenerationPanel({
  initialText = '',
  externalAudioUrl = null,
  fullPipelineActive = false,
  currentStageIndex = -1,
}) {
  const [text, setText] = useState(
    initialText ||
    'Electric vehicles are transforming the future of sustainable transportation across modern cities.'
  );
  const [language, setLanguage] = useState('en');
  const [status, setStatus] = useState('idle'); // idle | generating | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);

  // Sync initialText if passed from Qwen PlanViewer
  useEffect(() => {
    if (initialText) {
      setText(initialText);
      if (status === 'generating') {
        setStatus('idle');
      }
    }
  }, [initialText]);

  // Sync externalAudioUrl if generated in full pipeline
  useEffect(() => {
    if (externalAudioUrl) {
      setResult({
        audio_url: externalAudioUrl,
        duration: 'Synced',
        sample_rate: 22050,
        file_size_bytes: 250000,
        generation_time: 'Pipeline',
      });
      setStatus('done');
    }
  }, [externalAudioUrl]);

  const handleGenerateVoice = async () => {
    if (!text.trim()) return;

    setStatus('generating');
    setResult(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/generate-audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          language: language,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: 'Unknown server error' }));
        throw new Error(errData.error || errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'Voice generation failed');
      }

      setResult(data);
      setStatus('done');
    } catch (err) {
      setStatus('error');
      setError(err.message);
    }
  };

  // Determine stage state when full pipeline is running
  const isPipelineSynthesizing = fullPipelineActive && currentStageIndex === 5;
  const isPipelineWaiting = fullPipelineActive && currentStageIndex >= 0 && currentStageIndex < 5;
  const isPipelineVoiceDone = fullPipelineActive && currentStageIndex > 5;
  const isSynthesizing = status === 'generating' || isPipelineSynthesizing;

  return (
    <div className="card voice-gen-card">
      <div className="vg-header">
        <Volume2 size={18} className="icon-purple" />
        <h2 className="vg-title">Voice Generation</h2>
        <span className="voice-model-badge">Piper TTS (Local CPU)</span>
      </div>

      {/* Input controls */}
      <div className="voice-input-group">
        <div className="voice-lang-row">
          <label className="input-label" htmlFor="voice-lang-select">Language & Voice</label>
          <select
            id="voice-lang-select"
            className="voice-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={isSynthesizing || fullPipelineActive}
          >
            <option value="en">English (US) — Lessac Medium (Neural ONNX)</option>
          </select>
        </div>

        <div className="voice-textarea-group">
          <label className="input-label" htmlFor="voice-text-input">Narration Script Text</label>
          <textarea
            id="voice-text-input"
            className="voice-textarea"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to synthesize into spoken narration..."
            disabled={isSynthesizing || fullPipelineActive}
          />
        </div>
      </div>

      {/* Action button */}
      {!isSynthesizing && !fullPipelineActive && (
        <button
          id="generate-voice-btn"
          type="button"
          className="btn-generate-voice"
          onClick={handleGenerateVoice}
          disabled={!text.trim()}
        >
          <Mic size={16} />
          Generate Voice
        </button>
      )}

      {/* Pipeline waiting state (Steps 1-5) */}
      {isPipelineWaiting && (
        <div className="voice-waiting-notice" style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.875rem' }}>
          <Hourglass size={15} />
          <span>Waiting for pipeline... (Piper starts at Step 6)</span>
        </div>
      )}

      {/* Actively synthesizing (Step 6 or standalone) */}
      {isSynthesizing && (
        <div className="voice-running-notice">
          <Loader2 size={16} className="spin-animation" />
          <span>Synthesizing neural speech with Piper TTS on CPU...</span>
        </div>
      )}

      {/* Step 6 completed notice during remaining pipeline */}
      {isPipelineVoiceDone && status !== 'done' && (
        <div className="voice-done-stage-notice" style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)', display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontSize: '0.875rem' }}>
          <CheckCircle size={15} />
          <span>Voice generation completed</span>
        </div>
      )}

      {/* Error display */}
      {status === 'error' && (
        <div className="vg-error-box">
          <AlertTriangle size={18} className="vg-error-icon" />
          <div>
            <p className="vg-error-title">Voice Generation Failed</p>
            <p className="vg-error-message">{error}</p>
          </div>
          <button className="vg-retry-btn" onClick={() => setStatus('idle')}>
            Retry
          </button>
        </div>
      )}

      {/* Success / Audio player */}
      {status === 'done' && result && result.audio_url && (
        <div className="voice-result-box">
          <div className="vg-result-header">
            <CheckCircle size={16} className="vg-success-icon" />
            <span className="vg-result-title">Voice Generated Successfully</span>
          </div>

          <div className="audio-player-wrapper">
            <audio
              ref={audioRef}
              controls
              className="voice-audio-player"
              src={result.audio_url.startsWith('http') ? result.audio_url : `${API_BASE}${result.audio_url}`}
            >
              Your browser does not support the audio element.
            </audio>
          </div>

          <div className="vg-stats-grid">
            <div className="vg-stat">
              <Clock size={13} />
              <span>Duration: {result.duration}s · Sample Rate: {result.sample_rate || 22050} Hz</span>
            </div>
            <div className="vg-stat">
              <Music size={13} />
              <span>Size: {((result.file_size_bytes || 0) / 1024).toFixed(1)} KB</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
