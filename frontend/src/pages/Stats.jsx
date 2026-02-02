import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const formatRating = (value) => {
  if (value == null) {
    return "-";
  }
  return `★ ${value.toFixed(1)}`;
};

const StatsCard = ({ title, data }) => {
  if (!data) {
    return null;
  }
  return (
    <div className="summary-card">
      <div className="summary-title">{title}</div>
      <div className="summary-text">
        Средняя оценка за 7 дней: {formatRating(data.average_rating_7d)}
      </div>
      <div className="summary-text">
        Средняя оценка за 30 дней: {formatRating(data.average_rating_30d)}
      </div>
      <div className="summary-text">
        Запланировано: {data.planned_count}
      </div>
      <div className="summary-text">
        Завершено: {data.completed_count}
      </div>
    </div>
  );
};

const Stats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const loadStats = async () => {
      try {
        setLoading(true);
        const data = await request("/stats");
        if (!active) {
          return;
        }
        setStats(data);
        setError("");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    loadStats();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Статистика</h2>
            <p className="muted">
              Средние оценки за 7/30 дней и количество повторений.
            </p>
          </div>
          <span className="badge">7/30 дней</span>
        </div>
        {error && <div className="alert error">{error}</div>}
        {loading && <p className="muted">Загрузка статистики...</p>}
        {!loading && stats && (
          <div className="summary-grid">
            <StatsCard title="Теория" data={stats.theory} />
            <StatsCard title="Алгоритмы" data={stats.algorithms} />
          </div>
        )}
      </section>
    </div>
  );
};

export default Stats;
