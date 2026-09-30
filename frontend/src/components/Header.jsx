import React from 'react';
import { Video, Cpu, Activity } from 'lucide-react';

export default function Header({ backendStatus }) {
  const getStatusBadge = () => {
    switch (backendStatus) {
      case 'online':
        return (
          <span className="status-badge status-online">
            <span className="status-dot"></span>
            Backend Online
          </span>
        );
      case 'offline':
        return (
          <span className="status-badge status-offline">
            <span className="status-dot"></span>
            Backend Offline
          </span>
        );
      default:
        return (
          <span className="status-badge status-checking">
            <span className="status-dot"></span>
            Connecting...
          </span>
        );
    }
  };

  return (
    <header className="app-header">
      <div className="header-container">
        <div className="brand-group">
          <div className="brand-icon">
            <Video size={26} strokeWidth={2.2} />
          </div>
          <div>
            <h1 className="app-title">AI Video Generator</h1>
            <p className="app-subtitle">Create short videos using local AI models</p>
          </div>
        </div>

        <div className="header-meta">
          <div className="hardware-badge">
            <Cpu size={15} />
            <span>Low-Resource Mode (4GB VRAM Target)</span>
          </div>
          <div className="status-container">
            {getStatusBadge()}
          </div>
        </div>
      </div>
    </header>
  );
}
