import React from 'react';
import { Film, VideoOff, Download, CheckCircle, Clock, Volume2, Sparkles } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VideoOutput({ finalVideo }) {
  if (!finalVideo || !finalVideo.video_url) {
    return (
      <div className="card output-card">
        <div className="output-header">
          <Film size={18} className="icon-primary" />
          <h2 className="output-title">Video Output Preview</h2>
        </div>

        <div className="empty-output-container">
          <div className="empty-icon-wrapper">
            <VideoOff size={40} className="empty-icon" />
          </div>
          <h3 className="empty-title">Your assembled final video will appear here.</h3>
          <p className="empty-description">
            Run the pipeline or assemble video clips + voiceover to render the final MP4 with FFmpeg.
          </p>
        </div>
      </div>
    );
  }

  const videoSrc = `${API_BASE}${finalVideo.video_url}`;

  return (
    <div className="card output-card">
      <div className="output-header">
        <div className="final-header-left">
          <Film size={18} className="icon-primary" />
          <h2 className="output-title">Final Assembled Video</h2>
        </div>
        <span className="final-badge">FFmpeg (H.264 / AAC)</span>
      </div>

      <div className="final-video-container">
        <video
          key={videoSrc}
          controls
          playsInline
          className="final-player"
          src={videoSrc}
        >
          Your browser does not support HTML5 video.
        </video>
      </div>

      <div className="final-meta-box">
        <div className="final-stat-row">
          <div className="final-stat">
            <Clock size={13} className="stat-icon" />
            <span>Duration: {Number(finalVideo.duration || 0).toFixed(1)}s</span>
          </div>
          <div className="final-stat">
            <Volume2 size={13} className="stat-icon" />
            <span>Audio: {finalVideo.audio_codec || 'aac'} ({finalVideo.has_audio ? 'Voiceover included' : 'No audio'})</span>
          </div>
        </div>
        <div className="final-stat-row">
          <div className="final-stat">
            <Sparkles size={13} className="stat-icon" />
            <span>Resolution: {finalVideo.resolution || '720x480'} ({finalVideo.fps || 8} FPS)</span>
          </div>
          <div className="final-stat">
            <CheckCircle size={13} className="stat-icon-green" />
            <span>Size: {((finalVideo.size_bytes || 0) / 1024).toFixed(1)} KB</span>
          </div>
        </div>
      </div>

      <div className="final-actions">
        <a
          href={videoSrc}
          download={finalVideo.filename || 'ai_video.mp4'}
          className="btn-download-video"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download size={16} />
          <span>Download Video (MP4)</span>
        </a>
      </div>
    </div>
  );
}
