import React from 'react';
import { CheckCircle, AlertTriangle, Terminal, XCircle } from 'lucide-react';

export default function ResponseFeedback({ responseData, error, onDismissError }) {
  if (!responseData && !error) {
    return null;
  }

  return (
    <div className="feedback-section">
      {error && (
        <div className="alert-box alert-error">
          <div className="alert-icon-wrap">
            <AlertTriangle size={20} className="alert-icon" />
          </div>
          <div className="alert-content">
            <h4 className="alert-title">Connection / Validation Error</h4>
            <p className="alert-message">{error}</p>
          </div>
          {onDismissError && (
            <button type="button" className="alert-close-btn" onClick={onDismissError} aria-label="Dismiss">
              <XCircle size={18} />
            </button>
          )}
        </div>
      )}

      {responseData && !error && (
        <div className="alert-box alert-success">
          <div className="alert-icon-wrap">
            <CheckCircle size={20} className="alert-icon-success" />
          </div>
          <div className="alert-content">
            <h4 className="alert-title">Backend Response (Foundation Tested)</h4>
            <p className="alert-message">{responseData.message}</p>
            
            <div className="response-details">
              <div className="details-header">
                <Terminal size={14} />
                <span>Echoed Request Parameters</span>
              </div>
              <pre className="json-display">
                {JSON.stringify(responseData, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
