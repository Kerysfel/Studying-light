import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const AlgorithmGroups = () => {
  const [groups, setGroups] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createNotes, setCreateNotes] = useState("");
  const [createError, setCreateError] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  const loadGroups = async (searchValue = "") => {
    try {
      setLoading(true);
      setError("");
      const queryParam = searchValue.trim()
        ? `?query=${encodeURIComponent(searchValue.trim())}`
        : "";
      const data = await request(`/algorithm-groups${queryParam}`);
      setGroups(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  const handleSearch = (event) => {
    event.preventDefault();
    loadGroups(query);
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    setCreateError("");
    if (!createTitle.trim()) {
      setCreateError("Введите название группы.");
      return;
    }
    try {
      setCreateLoading(true);
      await request("/algorithm-groups", {
        method: "POST",
        body: JSON.stringify({
          title: createTitle.trim(),
          description: createDescription.trim() || null,
          notes: createNotes.trim() || null,
        }),
      });
      setCreateTitle("");
      setCreateDescription("");
      setCreateNotes("");
      await loadGroups(query);
    } catch (err) {
      setCreateError(getErrorMessage(err));
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Группы алгоритмов</h2>
            <p className="muted">
              Справочник групп с количеством и кратким описанием.
            </p>
          </div>
        </div>

        <form className="summary-card" onSubmit={handleCreate}>
          <div className="summary-title">Новая группа</div>
          <div className="form-grid">
            <div className="form-block full">
              <label>Название</label>
              <input
                value={createTitle}
                onChange={(event) => setCreateTitle(event.target.value)}
                placeholder="Например, Графы"
              />
            </div>
            <div className="form-block full">
              <label>Описание (опционально)</label>
              <textarea
                rows="2"
                value={createDescription}
                onChange={(event) => setCreateDescription(event.target.value)}
              />
            </div>
            <div className="form-block full">
              <label>Заметки (опционально)</label>
              <textarea
                rows="2"
                value={createNotes}
                onChange={(event) => setCreateNotes(event.target.value)}
              />
            </div>
          </div>
          {createError && <div className="alert error">{createError}</div>}
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={createLoading}
            >
              {createLoading ? "Сохранение..." : "Создать группу"}
            </button>
          </div>
        </form>

        <form className="form-inline" onSubmit={handleSearch}>
          <div className="form-block">
            <label>Поиск</label>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Например, графы"
            />
          </div>
          <button className="ghost-button" type="submit">
            Найти
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              setQuery("");
              loadGroups("");
            }}
          >
            Сбросить
          </button>
        </form>

        {loading && <p className="muted">Загрузка групп...</p>}
        {error && <div className="alert error">{error}</div>}
        {!loading && !groups.length && (
          <div className="empty-state">Группы пока не добавлены.</div>
        )}

        <div className="list">
          {groups.map((group) => (
            <div key={group.id} className="list-row">
              <div>
                <div className="list-title">{group.title}</div>
                {(group.description || group.notes) && (
                  <div className="list-meta">
                    {group.description || group.notes}
                  </div>
                )}
                {!group.description && !group.notes && (
                  <div className="list-meta">Описание отсутствует.</div>
                )}
              </div>
              <div className="list-actions">
                <span className="pill">
                  Алгоритмов: {group.algorithms_count}
                </span>
                <Link
                  className="ghost-button"
                  to={`/algorithm-groups/${group.id}`}
                >
                  Открыть
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AlgorithmGroups;
