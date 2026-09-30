import React, { useState, useRef } from 'react';
import { Video, Play, Loader2, AlertTriangle, CheckCircle, Cpu, Clock, Film } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const STEPS = [
  'Preparing Model',
  'Loading CogVideoX',
  'Generating Video',
  'Saving MP4',
  'Completed',
];

export default function VideoGenerationPanel({ scenePlan }) {
  const [status, setStatus] = useState('idle'); // idle | loading | generating | done | error
  const [currentStep, setCurrentStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);

  // Use first scene video_prompt if available, else fall back to a default
  const videoPrompt =
    scenePlan?.scenes?.[0]?.video_prompt ||
    'A modern electric car driving smoothly on a clean city road at sunset, cinematic camera movement, realistic lighting, detailed environment, smooth motion.';

  const handleGenerateVideo = async () => {
    setStatus('loading');
    setCurrentStep(0);
    setResult(null);
    setError(null);

    try {
      // Step 0 → Preparing
      await delay(300);
      setCurrentStep(1); // Loading CogVideoX

      const response = await fetch(`${API_BASE}/api/generate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: videoPrompt,
          duration: 6,
          aspect_ratio: '16:9',
        }),
      });

      // Steps progress during the long backend call (simulated — real step happens server side)
      setCurrentStep(2); // Generating Video

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: 'Unknown server error' }));
        throw new Error(errData.error || errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setCurrentStep(3); // Saving MP4

      if (!data.success) {
        throw new Error(data.error || 'Generation returned success: false');
      }

      await delay(300);
      setCurrentStep(4); // Completed
      setResult(data);
      setStatus('done');
    } catch (err) {
      setStatus('error');
      setError(err.message);
      setCurrentStep(-1);
    }
  };

  const delay = (ms) => new Promise((res) => setTimeout(res, ms));

  return (
    <div className="card video-gen-card">
      <div className="vg-header">
        <Film size={18} className="icon-primary" />
        <h2 className="vg-title">Video Generation</h2>
        <span className="vg-model-badge">CogVideoX-2B (Local)</span>
      </div>

      <div className="vg-prompt-preview">
        <span className="vg-prompt-label">Scene 1 Video Prompt:</span>
        <p className="vg-prompt-text">"{videoPrompt}"</p>
      </div>

      {/* Step Progress */}
      <div className="vg-steps">
        {STEPS.map((step, idx) => {
          const isDone = currentStep > idx;
          const isActive = currentStep === idx;
          return (
            <div
              key={step}
              className={`vg-step ${isDone ? 'vg-step-done' : isActive ? 'vg-step-active' : 'vg-step-idle'}`}
            >
              <div className="vg-step-dot">
                {isDone ? (
                  <CheckCircle size={16} className="vg-step-check" />
                ) : isActive ? (
                  <Loader2 size={16} className="vg-step-spinner" />
                ) : (
                  <span className="vg-step-num">{idx + 1}</span>
                )}
              </div>
              <span className="vg-step-label">{step}</span>
            </div>
          );
        })}
      </div>

      {/* Generate Button */}
      {status === 'idle' && (
        <button
          id="generate-test-video-btn"
          type="button"
          className="btn-generate-video"
          onClick={handleGenerateVideo}
        >
          <Play size={16} fill="currentColor" />
          Generate Test Video
        </button>
      )}

      {(status === 'loading' || status === 'generating') && (
        <div className="vg-running-notice">
          <Loader2 size={16} className="spin-animation" />
          <span>
            {currentStep <= 1
              ? 'Loading CogVideoX-2B model into memory...'
              : 'Generating video frames (this may take several minutes on CPU)...'}
          </span>
        </div>
      )}

      {/* Error Display */}
      {status === 'error' && (
        <div className="vg-error-box">
          <AlertTriangle size={18} className="vg-error-icon" />
          <div>
            <p className="vg-error-title">Video Generation Failed</p>
            <p className="vg-error-message">{error}</p>
          </div>
          <button className="vg-retry-btn" onClick={() => { setStatus('idle'); setCurrentStep(-1); }}>
            Retry
          </button>
        </div>
      )}

      {/* Success — video player */}
      {status === 'done' && result && (
        <div className="vg-result">
          <div className="vg-result-header">
            <CheckCircle size={16} className="vg-success-icon" />
            <span className="vg-result-title">Video Generated Successfully</span>
          </div>

          <div className="vg-player-wrapper">
            <video
              ref={videoRef}
              controls
              playsInline
              className="vg-player"
              src={`${API_BASE}${result.video_url}`}
            >
              Your browser does not support HTML5 video.
            </video>
          </div>

          <div className="vg-stats-grid">
            <div className="vg-stat">
              <Clock size={13} />
              <span>{result.duration}s · {result.fps} FPS · {result.frames} frames</span>
            </div>
            <div className="vg-stat">
              <Cpu size={13} />
              <span>{result.width}×{result.height} · Gen: {result.generation_time}s</span>
            </div>
            <div className="vg-stat">
              <Film size={13} />
              <span>Size: {(result.file_size_bytes / 1024).toFixed(1)} KB · Total: {result.total_time}s</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
