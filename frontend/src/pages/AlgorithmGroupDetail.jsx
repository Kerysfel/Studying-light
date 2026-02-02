import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const AlgorithmGroupDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editError, setEditError] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [mergeOptions, setMergeOptions] = useState([]);
  const [mergeError, setMergeError] = useState("");
  const [mergeLoading, setMergeLoading] = useState(false);

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
        setEditTitle(data.title || "");
        setEditDescription(data.description || "");
        setEditNotes(data.notes || "");
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

  useEffect(() => {
    let active = true;
    const loadMergeOptions = async () => {
      try {
        const data = await request("/algorithm-groups");
        if (!active) {
          return;
        }
        const filtered = data.filter((item) => String(item.id) !== String(id));
        setMergeOptions(filtered);
      } catch (err) {
        if (!active) {
          return;
        }
        setMergeOptions([]);
      }
    };
    loadMergeOptions();
    return () => {
      active = false;
    };
  }, [id]);

  const handleEditSave = async () => {
    setEditError("");
    if (!editTitle.trim()) {
      setEditError("Введите название группы.");
      return;
    }
    try {
      setEditLoading(true);
      const response = await request(`/algorithm-groups/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle.trim(),
          description: editDescription.trim() || null,
          notes: editNotes.trim() || null,
        }),
      });
      setGroup(response);
      setEditMode(false);
    } catch (err) {
      setEditError(getErrorMessage(err));
    } finally {
      setEditLoading(false);
    }
  };

  const handleEditCancel = () => {
    setEditMode(false);
    setEditError("");
    setEditTitle(group?.title || "");
    setEditDescription(group?.description || "");
    setEditNotes(group?.notes || "");
  };

  const handleMerge = async () => {
    setMergeError("");
    if (!mergeTargetId) {
      setMergeError("Выберите целевую группу.");
      return;
    }
    try {
      setMergeLoading(true);
      const response = await request(`/algorithm-groups/${id}/merge`, {
        method: "POST",
        body: JSON.stringify({
          target_group_id: Number(mergeTargetId),
        }),
      });
      navigate(`/algorithm-groups/${response.id}`);
    } catch (err) {
      setMergeError(getErrorMessage(err));
    } finally {
      setMergeLoading(false);
    }
  };

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
          <div className="list-actions">
            <Link className="ghost-button" to="/algorithm-groups">
              Назад к группам
            </Link>
            <button
              className="primary-button"
              type="button"
              onClick={() => setEditMode(true)}
            >
              Редактировать
            </button>
          </div>
        </div>

        {editMode ? (
          <div className="summary-card">
            <div className="summary-title">Редактирование группы</div>
            <div className="form-grid">
              <div className="form-block full">
                <label>Название</label>
                <input
                  value={editTitle}
                  onChange={(event) => setEditTitle(event.target.value)}
                />
              </div>
              <div className="form-block full">
                <label>Описание</label>
                <textarea
                  rows="2"
                  value={editDescription}
                  onChange={(event) => setEditDescription(event.target.value)}
                />
              </div>
              <div className="form-block full">
                <label>Заметки</label>
                <textarea
                  rows="2"
                  value={editNotes}
                  onChange={(event) => setEditNotes(event.target.value)}
                />
              </div>
            </div>
            {editError && <div className="alert error">{editError}</div>}
            <div className="form-actions">
              <button
                className="ghost-button"
                type="button"
                onClick={handleEditCancel}
              >
                Отмена
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={handleEditSave}
                disabled={editLoading}
              >
                {editLoading ? "Сохранение..." : "Сохранить"}
              </button>
            </div>
          </div>
        ) : (
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
        )}

        {mergeOptions.length > 0 && (
          <div className="summary-card">
            <div className="summary-title">Merge groups</div>
            <div className="summary-text">
              Перенести все алгоритмы в другую группу и удалить текущую.
            </div>
            <div className="form-inline">
              <div className="form-block">
                <label>Целевая группа</label>
                <select
                  value={mergeTargetId}
                  onChange={(event) => setMergeTargetId(event.target.value)}
                >
                  <option value="">Выберите группу</option>
                  {mergeOptions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="ghost-button"
                type="button"
                onClick={handleMerge}
                disabled={mergeLoading}
              >
                {mergeLoading ? "Merge..." : "Merge"}
              </button>
            </div>
            {mergeError && <div className="alert error">{mergeError}</div>}
          </div>
        )}

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
