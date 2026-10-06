import { useState, useEffect } from 'react';
import { api } from '../api';
import './Settings.css';

export default function Settings({ onClose }) {
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedCouncil, setSelectedCouncil] = useState([]);
  const [selectedChairman, setSelectedChairman] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getConfig().then((config) => {
      setAvailableModels(config.available_models);
      setSelectedCouncil(config.council_models);
      setSelectedChairman(config.chairman_model);
    });
  }, []);

  const toggleCouncilModel = (model) => {
    setSelectedCouncil((prev) =>
      prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model]
    );
  };

  const handleSave = async () => {
    if (selectedCouncil.length < 2) {
      setError('Select at least 2 council models.');
      return;
    }
    if (!selectedChairman) {
      setError('Select a chairman model.');
      return;
    }
    setError(null);
    setIsSaving(true);
    try {
      await api.updateConfig(selectedCouncil, selectedChairman);
      onClose();
    } catch (e) {
      setError('Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const shortName = (model) => model.split('/')[1] || model;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Council Configuration</h2>
          <button className="settings-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="settings-body">
          <section className="settings-section">
            <h3>Council Models</h3>
            <p className="settings-hint">Select at least 2 models to participate in the council.</p>
            <div className="model-checklist">
              {availableModels.map((model) => (
                <label key={model} className="model-checkbox-row">
                  <input
                    type="checkbox"
                    checked={selectedCouncil.includes(model)}
                    onChange={() => toggleCouncilModel(model)}
                  />
                  <span className="model-label-short">{shortName(model)}</span>
                  <span className="model-label-full">{model}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="settings-section">
            <h3>Chairman Model</h3>
            <p className="settings-hint">Synthesizes the final answer from all responses and rankings.</p>
            <div className="model-checklist">
              {availableModels.map((model) => (
                <label key={model} className="model-checkbox-row">
                  <input
                    type="radio"
                    name="chairman"
                    checked={selectedChairman === model}
                    onChange={() => setSelectedChairman(model)}
                  />
                  <span className="model-label-short">{shortName(model)}</span>
                  <span className="model-label-full">{model}</span>
                </label>
              ))}
            </div>
          </section>
        </div>

        {error && <div className="settings-error">{error}</div>}

        <div className="settings-footer">
          <button className="settings-cancel-btn" onClick={onClose}>Cancel</button>
          <button className="settings-save-btn" onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
