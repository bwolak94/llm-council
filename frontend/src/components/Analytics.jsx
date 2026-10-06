import { useState, useEffect } from 'react';
import { api } from '../api';
import './Analytics.css';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .catch(() => setError('Failed to load analytics'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="analytics">
        <div className="analytics-loading">Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics">
        <div className="analytics-error">{error}</div>
      </div>
    );
  }

  const models = data?.models ?? [];
  const totalConversations = data?.total_conversations ?? 0;

  const shortName = (model) => model.split('/')[1] || model;

  // Normalize rank score: rank 1 = 100%, worst rank = 0%
  const maxRank = models.length > 0 ? Math.max(...models.map((m) => m.average_rank)) : 1;
  const rankScore = (avgRank) =>
    maxRank <= 1 ? 100 : Math.round(((maxRank - avgRank) / (maxRank - 1)) * 100);

  return (
    <div className="analytics">
      <div className="analytics-header">
        <h2>Model Performance Analytics</h2>
        <p className="analytics-subtitle">
          Based on {totalConversations} conversation{totalConversations !== 1 ? 's' : ''} with persisted rankings
        </p>
      </div>

      {models.length === 0 ? (
        <div className="analytics-empty">
          <p>No ranking data yet.</p>
          <p>Start a conversation and rankings will appear here after Stage 2 completes.</p>
        </div>
      ) : (
        <div className="analytics-body">
          <section className="analytics-section">
            <h3>Average Rank <span className="section-hint">(lower rank = better performance)</span></h3>
            <div className="chart">
              {models.map((m) => (
                <div key={m.model} className="chart-row">
                  <div className="chart-label" title={m.model}>{shortName(m.model)}</div>
                  <div className="chart-bar-wrap">
                    <div
                      className="chart-bar chart-bar-rank"
                      style={{ width: `${rankScore(m.average_rank)}%` }}
                    />
                  </div>
                  <div className="chart-value">{m.average_rank}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="analytics-section">
            <h3>Win Rate <span className="section-hint">(% of conversations ranked #1)</span></h3>
            <div className="chart">
              {[...models].sort((a, b) => b.win_rate - a.win_rate).map((m) => (
                <div key={m.model} className="chart-row">
                  <div className="chart-label" title={m.model}>{shortName(m.model)}</div>
                  <div className="chart-bar-wrap">
                    <div
                      className="chart-bar chart-bar-win"
                      style={{ width: `${Math.round(m.win_rate * 100)}%` }}
                    />
                  </div>
                  <div className="chart-value">{Math.round(m.win_rate * 100)}%</div>
                </div>
              ))}
            </div>
          </section>

          <section className="analytics-section">
            <h3>Summary Table</h3>
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Conversations</th>
                  <th>Avg Rank</th>
                  <th>Wins</th>
                  <th>Win Rate</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.model}>
                    <td>
                      <span className="table-model-short">{shortName(m.model)}</span>
                      <span className="table-model-full">{m.model}</span>
                    </td>
                    <td>{m.appearances}</td>
                    <td>{m.average_rank}</td>
                    <td>{m.wins}</td>
                    <td>{Math.round(m.win_rate * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  );
}
