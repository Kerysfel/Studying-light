import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const AlgorithmGroupDetail = () => {
  const { id } = useParams();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const loadGroup = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await request(`/algorithm-groups/${id}`);
        if (!active) {
          return;
        }
        setGroup(data);
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
    loadGroup();
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return <p className="muted">Загрузка группы...</p>;
  }

  if (error) {
    return <div className="alert error">{error}</div>;
  }

  if (!group) {
    return null;
  }

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>{group.title}</h2>
            <p className="muted">Алгоритмы в группе.</p>
          </div>
          <Link className="ghost-button" to="/algorithm-groups">
            Назад к группам
          </Link>
        </div>

        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-title">Описание</div>
            <div className="summary-text">
              {group.description || "Описание отсутствует."}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Заметки</div>
            <div className="summary-text">
              {group.notes || "Заметки отсутствуют."}
            </div>
          </div>
        </div>

        <div className="summary-block">
          <div className="summary-title">Алгоритмы</div>
          <div className="summary-value">
            Всего: {group.algorithms?.length || 0}
          </div>
        </div>

        <div className="list">
          {(group.algorithms || []).map((algorithm) => (
            <div key={algorithm.id} className="list-row">
              <div>
                <div className="list-title">{algorithm.title}</div>
                {algorithm.summary && (
                  <div className="list-meta">{algorithm.summary}</div>
                )}
                {algorithm.complexity && (
                  <div className="list-meta">
                    Сложность: {algorithm.complexity}
                  </div>
                )}
              </div>
              <Link
                className="ghost-button"
                to={`/algorithms/${algorithm.id}`}
              >
                Открыть
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AlgorithmGroupDetail;
