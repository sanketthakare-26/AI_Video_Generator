import React from 'react';
import { Layers, Info, CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';

export default function PipelineProgress({
  hasPlan,
  isGenerating,
  fullPipelineActive,
  currentStageIndex = -1,
  progressMessage = '',
  hasError = false,
}) {
  const defaultStages = [
    { id: 'prompt', label: '1. Understanding Prompt', engine: 'Qwen2.5-1.5B' },
    { id: 'script', label: '2. Creating Script', engine: 'Qwen2.5-1.5B' },
    { id: 'planning', label: '3. Planning Scenes', engine: 'Qwen2.5-1.5B' },
    { id: 'scene1', label: '4. Generating Scene 1', engine: 'CogVideoX-2B' },
    { id: 'scene2', label: '5. Generating Scene 2 / 3', engine: 'CogVideoX-2B' },
    { id: 'voice', label: '6. Generating Voice', engine: 'Piper TTS' },
    { id: 'subtitles', label: '7. Creating Subtitles', engine: 'SRT Generator' },
    { id: 'assembly', label: '8. Assembling Final Video', engine: 'FFmpeg' },
    { id: 'completed', label: '9. Completed', engine: 'Final MP4' },
  ];

  return (
    <div className="card progress-card">
      <div className="progress-card-header">
        <div className="progress-title-group">
          <Layers size={18} className="icon-primary" />
          <h2 className="progress-title">End-to-End Pipeline Progress</h2>
        </div>
        <span className="pipeline-mode-tag">Sequential Execution (4GB VRAM)</span>
      </div>

      <p className="pipeline-desc">
        Real-time pipeline stages (Qwen → CogVideoX → Piper → FFmpeg):
      </p>

      {progressMessage && fullPipelineActive && (
        <div className="pipeline-live-banner">
          <Loader2 size={14} className="spin-animation" />
          <span>{progressMessage}</span>
        </div>
      )}

      <div className="stages-list">
        {defaultStages.map((stage, idx) => {
          let isDone = false;
          let isActive = false;

          if (fullPipelineActive) {
            isDone = currentStageIndex > idx;
            isActive = currentStageIndex === idx;
          } else if (hasPlan) {
            // Plan only mode
            isDone = idx < 3;
          } else if (isGenerating) {
            isActive = idx === 0;
          }

          let statusClass = 'stage-inactive';
          let statusText = 'Standby';

          if (isDone) {
            statusClass = 'stage-completed';
            statusText = 'Completed ✓';
          } else if (isActive) {
            statusClass = 'stage-active';
            statusText = 'Processing...';
          }

          return (
            <div key={stage.id} className={`stage-item ${statusClass}`}>
              <div className="stage-index-badge">
                {isDone ? (
                  <CheckCircle2 size={16} className="stage-done-icon" />
                ) : isActive ? (
                  <Loader2 size={15} className="stage-spinner-icon spin-animation" />
                ) : (
                  <Circle size={15} className="stage-circle-icon" />
                )}
              </div>
              <div className="stage-content">
                <span className="stage-name">{stage.label}</span>
                <span className="stage-engine">({stage.engine})</span>
              </div>
              <div className="stage-status-label">{statusText}</div>
            </div>
          );
        })}
      </div>

      <div className="pipeline-notice">
        <Info size={16} className="notice-icon" />
        <span>
          {fullPipelineActive
            ? progressMessage || 'Executing sequential pipeline: AI models load and unload automatically to ensure zero OOM.'
            : hasPlan
            ? 'Qwen plan ready. Click "Generate Full Video" to render scene clips and assemble final video.'
            : 'Enter prompt and click "Generate Video Plan" or "Generate Full Video" to start.'}
        </span>
      </div>
    </div>
  );
}
