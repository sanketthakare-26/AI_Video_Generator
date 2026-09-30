import React, { useState } from 'react';
import { Film, Copy, Check, Clapperboard, Mic, Sparkles, Clock, Palette } from 'lucide-react';

export default function PlanViewer({ plan, onGenerateVoiceover }) {
  const [copiedVoiceover, setCopiedVoiceover] = useState(false);
  const [copiedSceneIndex, setCopiedSceneIndex] = useState(null);

  if (!plan) return null;

  const handleCopyVoiceover = () => {
    navigator.clipboard.writeText(plan.voiceover);
    setCopiedVoiceover(true);
    setTimeout(() => setCopiedVoiceover(false), 2000);
  };

  const handleCopyPrompt = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedSceneIndex(index);
    setTimeout(() => setCopiedSceneIndex(null), 2000);
  };

  return (
    <div className="card plan-viewer-card">
      <div className="plan-header">
        <div className="plan-title-wrapper">
          <Clapperboard size={22} className="icon-primary" />
          <div>
            <h2 className="plan-main-title">{plan.title}</h2>
            <div className="plan-meta-tags">
              <span className="meta-badge style-badge">
                <Palette size={13} />
                <span>{plan.style}</span>
              </span>
              <span className="meta-badge duration-badge">
                <Clock size={13} />
                <span>{plan.total_duration}s Total ({plan.scenes.length} Scenes)</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Voiceover / Narration Script */}
      <div className="voiceover-section">
        <div className="section-label-row">
          <span className="section-label">
            <Mic size={15} className="icon-primary" />
            Voiceover Narration Script
          </span>
          <div className="voiceover-actions">
            {onGenerateVoiceover && (
              <button
                type="button"
                className="btn-plan-voiceover"
                onClick={() => onGenerateVoiceover(plan.voiceover)}
                title="Send narration to Piper TTS"
              >
                <Mic size={13} />
                <span>Generate Voiceover</span>
              </button>
            )}
            <button
              type="button"
              className="copy-btn"
              onClick={handleCopyVoiceover}
              title="Copy voiceover script"
            >
              {copiedVoiceover ? <Check size={14} className="copied-icon" /> : <Copy size={14} />}
              <span>{copiedVoiceover ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>
        <p className="voiceover-text">"{plan.voiceover}"</p>
      </div>


      {/* Scene Storyboards */}
      <div className="scenes-section">
        <h3 className="section-title">
          <Film size={16} className="icon-primary" />
          <span>Scene Storyboard & Video Diffusion Prompts</span>
        </h3>

        <div className="scenes-grid">
          {plan.scenes.map((scene, idx) => (
            <div key={scene.scene_number || idx} className="scene-card">
              <div className="scene-header">
                <span className="scene-num-badge">Scene {scene.scene_number}</span>
                <span className="scene-duration">{scene.duration}s</span>
              </div>

              <div className="scene-body">
                <div className="scene-desc-block">
                  <span className="field-label">Visual Action:</span>
                  <p className="scene-desc-text">{scene.description}</p>
                </div>

                <div className="scene-prompt-block">
                  <div className="prompt-header-row">
                    <span className="field-label video-prompt-label">
                      <Sparkles size={13} className="icon-sparkle" /> Future Video Model Prompt:
                    </span>
                    <button
                      type="button"
                      className="mini-copy-btn"
                      onClick={() => handleCopyPrompt(scene.video_prompt, idx)}
                      title="Copy video diffusion prompt"
                    >
                      {copiedSceneIndex === idx ? <Check size={12} className="copied-icon" /> : <Copy size={12} />}
                    </button>
                  </div>
                  <code className="video-prompt-code">{scene.video_prompt}</code>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
