import { useState, useEffect, useCallback } from 'react';
import { checkHealth, generateVideo } from '../services/api';

export function useVideoGeneration() {
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState(15);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [language, setLanguage] = useState('English');
  
  const [backendStatus, setBackendStatus] = useState('checking'); // 'online' | 'offline' | 'checking'
  const [isGenerating, setIsGenerating] = useState(false);
  const [responseData, setResponseData] = useState(null);
  const [error, setError] = useState(null);

  // Poll backend health without disrupting 'online' status
  const verifyBackend = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) {
        setBackendStatus('checking');
      }
      const data = await checkHealth();
      if (data && data.status === 'ok') {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch (err) {
      setBackendStatus('offline');
    }
  }, []);

  useEffect(() => {
    // Initial verification
    verifyBackend(true);
    // Background polling every 10s (never resets status to 'checking')
    const interval = setInterval(() => verifyBackend(false), 10000);
    return () => clearInterval(interval);
  }, [verifyBackend]);

  const handleGenerate = async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setError('Prompt cannot be empty. Please enter a description.');
      return;
    }

    setError(null);
    setResponseData(null);
    setIsGenerating(true);

    try {
      const payload = {
        prompt: trimmedPrompt,
        duration,
        aspect_ratio: aspectRatio,
        language,
      };

      const response = await generateVideo(payload);
      setResponseData(response);
      setBackendStatus('online');
    } catch (err) {
      setError(err.message || 'An unexpected error occurred communicating with the backend.');
    } finally {
      setIsGenerating(false);
    }
  };

  const dismissError = () => setError(null);

  return {
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
    isPromptEmpty: !prompt.trim(),
  };
}
