import React from 'react';
import { Clock, Ratio, Languages, Play, Sparkles, Loader2 } from 'lucide-react';

export default function VideoSettings({
  duration,
  setDuration,
  aspectRatio,
  setAspectRatio,
  language,
  setLanguage,
  onGenerate,
  onGenerateFull,
  isGenerating,
  isFullGenerating,
  isPromptEmpty,
}) {
  const isBusy = isGenerating || isFullGenerating;

  return (
    <div className="card settings-card">
      <h2 className="settings-title">Video Settings</h2>

      <div className="settings-grid">
        {/* Duration */}
        <div className="setting-group">
          <label htmlFor="duration-select" className="setting-label">
            <Clock size={16} />
            <span>Duration</span>
          </label>
          <select
            id="duration-select"
            className="select-input"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            disabled={isBusy}
          >
            <option value={10}>10 seconds (2 Scenes · Fast Test)</option>
            <option value={15}>15 seconds (3 Scenes · Recommended)</option>
            <option value={20}>20 seconds (4 Scenes)</option>
            <option value={30}>30 seconds (5 Scenes)</option>
          </select>
        </div>

        {/* Aspect Ratio */}
        <div className="setting-group">
          <label htmlFor="aspect-select" className="setting-label">
            <Ratio size={16} />
            <span>Aspect Ratio</span>
          </label>
          <select
            id="aspect-select"
            className="select-input"
            value={aspectRatio}
            onChange={(e) => setAspectRatio(e.target.value)}
            disabled={isBusy}
          >
            <option value="16:9">16:9 (Landscape / YouTube)</option>
            <option value="9:16">9:16 (Portrait / Reels / Shorts)</option>
            <option value="1:1">1:1 (Square / Feed)</option>
          </select>
        </div>

        {/* Voice Language */}
        <div className="setting-group">
          <label htmlFor="language-select" className="setting-label">
            <Languages size={16} />
            <span>Voice Narration</span>
          </label>
          <select
            id="language-select"
            className="select-input"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={isBusy}
          >
            <option value="English">English (US · Piper Lessac)</option>
            <option value="Hindi">Hindi (Upcoming)</option>
          </select>
        </div>
      </div>

      <div className="generate-actions-row">
        {/* Plan Generation Button */}
        <button
          id="generate-video-btn"
          type="button"
          className="btn-secondary-plan"
          disabled={isPromptEmpty || isBusy}
          onClick={onGenerate}
          title="Generate Video Plan & Script using Qwen LLM"
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="spin-animation" />
              <span>Generating Plan...</span>
            </>
          ) : (
            <>
              <Play size={16} />
              <span>Generate Video Plan</span>
            </>
          )}
        </button>

        {/* Full Pipeline Button */}
        <button
          id="generate-full-video-btn"
          type="button"
          className="btn-primary-generate"
          disabled={isPromptEmpty || isBusy}
          onClick={onGenerateFull}
          title="Run entire end-to-end pipeline: Qwen -> CogVideoX -> Piper -> FFmpeg -> Final MP4"
        >
          {isFullGenerating ? (
            <>
              <Loader2 size={18} className="spin-animation" />
              <span>Running Full Pipeline...</span>
            </>
          ) : (
            <>
              <Sparkles size={18} />
              <span>Generate Full Video</span>
            </>
          )}
        </button>
      </div>

      {isPromptEmpty && (
        <p className="generate-hint">Enter a prompt above to enable video generation.</p>
      )}
    </div>
  );
}
