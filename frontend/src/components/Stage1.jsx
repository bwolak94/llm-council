import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import './Stage1.css';

export default function Stage1({ responses, failedModels = [], conversationId }) {
  const [localResponses, setLocalResponses] = useState(responses);
  const [localFailed, setLocalFailed] = useState(failedModels);
  const [retrying, setRetrying] = useState({});
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    setLocalResponses(responses);
  }, [responses]);

  useEffect(() => {
    setLocalFailed(failedModels);
  }, [failedModels]);

  const handleRetry = async (model) => {
    setRetrying((prev) => ({ ...prev, [model]: true }));
    try {
      const result = await api.retryModel(conversationId, model);
      setLocalResponses((prev) => [...prev, result]);
      setLocalFailed((prev) => prev.filter((m) => m !== model));
      setActiveTab(localResponses.length); // Switch to the new tab
    } catch (e) {
      console.error('Retry failed:', e);
    } finally {
      setRetrying((prev) => ({ ...prev, [model]: false }));
    }
  };

  if (!localResponses || localResponses.length === 0) {
    return null;
  }

  const activeResponse = localResponses[activeTab];

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {localResponses.map((resp, index) => (
          <button
            key={resp.model}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
          </button>
        ))}
        {localFailed.map((model) => (
          <button
            key={model}
            className="tab tab-failed"
            onClick={() => {}}
          >
            {model.split('/')[1] || model} ✕
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="tab-content-header">
          <div className="model-name">{activeResponse.model}</div>
          {activeResponse.usage && (
            <div className="token-badge">
              {activeResponse.usage.total_tokens?.toLocaleString()} tokens
            </div>
          )}
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{activeResponse.response}</ReactMarkdown>
        </div>
      </div>

      {localFailed.length > 0 && (
        <div className="failed-models">
          {localFailed.map((model) => (
            <div key={model} className="failed-model-row">
              <span className="failed-model-name">{model}</span>
              <span className="failed-model-label">failed to respond</span>
              <button
                className="retry-btn"
                onClick={() => handleRetry(model)}
                disabled={retrying[model]}
              >
                {retrying[model] ? 'Retrying...' : 'Retry'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
