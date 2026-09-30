import React from 'react';
import { Sparkles, MessageSquare } from 'lucide-react';

export default function PromptSection({ prompt, setPrompt, disabled }) {
  const examplePrompt = "Create a cinematic 20-second video of an electric car driving through a futuristic city.";

  const handleUseExample = () => {
    if (!disabled) {
      setPrompt(examplePrompt);
    }
  };

  return (
    <div className="card prompt-card">
      <div className="card-header">
        <label htmlFor="prompt-input" className="card-title">
          <MessageSquare size={18} className="icon-primary" />
          <span>Describe Your Video</span>
        </label>
        <span className="char-count">{prompt.length} characters</span>
      </div>

      <div className="textarea-wrapper">
        <textarea
          id="prompt-input"
          className="prompt-textarea"
          rows={4}
          placeholder="Describe the video you want to create..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div className="example-prompt-container">
        <span className="example-label">
          <Sparkles size={14} className="icon-sparkle" /> Example Prompt:
        </span>
        <button
          type="button"
          className="example-prompt-btn"
          onClick={handleUseExample}
          disabled={disabled}
          title="Click to use this example"
        >
          "{examplePrompt}"
        </button>
      </div>
    </div>
  );
}
