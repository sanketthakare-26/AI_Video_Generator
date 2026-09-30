import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import PromptSection from './components/PromptSection';
import VideoSettings from './components/VideoSettings';
import PipelineProgress from './components/PipelineProgress';
import VideoOutput from './components/VideoOutput';
import PlanViewer from './components/PlanViewer';
import VideoGenerationPanel from './components/VideoGenerationPanel';
import VoiceGenerationPanel from './components/VoiceGenerationPanel';
import ResponseFeedback from './components/ResponseFeedback';
import { useVideoGeneration } from './hooks/useVideoGeneration';
import './styles/App.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function App() {
  const {
    prompt,
    setPrompt,
    duration,
    setDuration,
    aspectRatio,
    setAspectRatio,
    language,
    setLanguage,
    backendStatus,
    isGenerating,
    responseData,
    error,
    dismissError,
    handleGenerate,
    isPromptEmpty,
  } = useVideoGeneration();

  const [activeVoiceText, setActiveVoiceText] = useState('');
  const [isFullGenerating, setIsFullGenerating] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(-1);
  const [currentProgressMsg, setCurrentProgressMsg] = useState('');
  const [finalVideoData, setFinalVideoData] = useState(null);
  const [fullPipelineError, setFullPipelineError] = useState(null);

  const pollIntervalRef = useRef(null);

  const generatedPlan = responseData?.plan || finalVideoData?.plan;

  const handlePlanVoiceover = (voiceoverText) => {
    setActiveVoiceText(voiceoverText);
    setTimeout(() => {
      const el = document.getElementById('generate-voice-btn');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  };

  // Real-time backend status polling during full generation
  const startStatusPolling = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/pipeline-status`);
        if (!res.ok) return;
        const status = await res.json();

        if (status.is_running) {
          if (status.current_stage_index !== undefined && status.current_stage_index >= 0) {
            setCurrentStageIndex(status.current_stage_index);
          }
          if (status.progress_message) {
            setCurrentProgressMsg(status.progress_message);
          }
        } else if (status.error) {
          clearInterval(pollIntervalRef.current);
          setFullPipelineError(`Video assembly failed: ${status.error}`);
          setCurrentStageIndex(-1);
          setIsFullGenerating(false);
        }
      } catch (e) {
        // Ignore transient polling network errors
      }
    }, 1000);
  };

  const stopStatusPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopStatusPolling();
  }, []);

  const handleGenerateFull = async () => {
    if (!prompt.trim()) return;

    setIsFullGenerating(true);
    setCurrentStageIndex(0);
    setCurrentProgressMsg('Starting full pipeline execution...');
    setFinalVideoData(null);
    setFullPipelineError(null);

    startStatusPolling();

    try {
      const res = await fetch(`${API_BASE}/api/generate-full-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          duration: duration,
          aspect_ratio: aspectRatio,
          language: language,
          burn_subtitles: false,
        }),
      });

      stopStatusPolling();

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: 'Server error' }));
        throw new Error(errData.error || errData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error || 'Full video generation failed');
      }

      setCurrentStageIndex(8); // Completed
      setCurrentProgressMsg('Video assembled successfully!');
      setFinalVideoData(data);
    } catch (err) {
      stopStatusPolling();
      setFullPipelineError(err.message.includes('failed') ? err.message : `Video assembly failed: ${err.message}`);
      setCurrentStageIndex(-1);
    } finally {
      setIsFullGenerating(false);
    }
  };

  return (
    <div className="app-layout">
      <Header backendStatus={backendStatus} />

      <main className="main-content">
        <div className="content-container">
          {/* Left Column: Controls, Settings & Plan Viewer */}
          <div className="column column-primary">
            <PromptSection
              prompt={prompt}
              setPrompt={setPrompt}
              disabled={isGenerating || isFullGenerating}
            />

            <VideoSettings
              duration={duration}
              setDuration={setDuration}
              aspectRatio={aspectRatio}
              setAspectRatio={setAspectRatio}
              language={language}
              setLanguage={setLanguage}
              onGenerate={handleGenerate}
              onGenerateFull={handleGenerateFull}
              isGenerating={isGenerating}
              isFullGenerating={isFullGenerating}
              isPromptEmpty={isPromptEmpty}
            />

            <ResponseFeedback
              responseData={responseData}
              error={error || fullPipelineError}
              onDismissError={() => {
                dismissError();
                setFullPipelineError(null);
              }}
            />

            {generatedPlan && (
              <PlanViewer
                plan={generatedPlan}
                onGenerateVoiceover={handlePlanVoiceover}
              />
            )}

            {generatedPlan && <VideoGenerationPanel scenePlan={generatedPlan} />}
            <VoiceGenerationPanel
              initialText={activeVoiceText || generatedPlan?.voiceover || ''}
              externalAudioUrl={finalVideoData?.audio_url}
              fullPipelineActive={isFullGenerating}
              currentStageIndex={currentStageIndex}
            />
          </div>

          {/* Right Column: Pipeline Status & Output Preview */}
          <div className="column column-secondary">
            <VideoOutput finalVideo={finalVideoData} />
            <PipelineProgress
              hasPlan={Boolean(generatedPlan)}
              isGenerating={isGenerating}
              fullPipelineActive={isFullGenerating}
              currentStageIndex={currentStageIndex}
              progressMessage={currentProgressMsg}
            />
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-container">
          <p>
            <strong>AI Video Generator</strong> — Powered by local Qwen2.5-1.5B, CogVideoX-2B, Piper TTS & FFmpeg on Windows (8GB RAM / 4GB VRAM RTX 2050 target).
          </p>
          <p className="footer-subtext">
            Fully local sequential pipeline architecture: Qwen (Scripting) → CogVideoX (Clips) → Piper (Voice) → FFmpeg (Assembly). Zero cloud APIs.
          </p>
        </div>
      </footer>
    </div>
  );
}
