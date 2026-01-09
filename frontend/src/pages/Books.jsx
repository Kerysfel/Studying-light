import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const formatReadingDuration = (value) => {
  const totalSeconds = Number(value);
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) {
    return "0 мин";
  }
  const totalMinutes = Math.floor(totalSeconds / 60);
  if (totalMinutes < 60) {
    return `${totalMinutes} мин`;
  }
  const totalHours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (totalHours < 24) {
    return minutes ? `${totalHours} ч ${minutes} мин` : `${totalHours} ч`;
  }
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  if (days < 30) {
    return hours ? `${days} дн ${hours} ч` : `${days} дн`;
  }
  const months = Math.floor(days / 30);
  return `${months} мес`;
};

const Books = () => {
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [pagesTotal, setPagesTotal] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await request("/books");
        if (!active) {
          return;
        }
        setItems(data);
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
    load();
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    if (!title.trim()) {
      setFormError("Укажите название книги.");
      return;
    }
    const pagesValue = pagesTotal.trim();
    const pagesTotalValue = pagesValue ? Number(pagesValue) : null;
    if (
      pagesValue &&
      (!Number.isInteger(pagesTotalValue) || pagesTotalValue <= 0)
    ) {
      setFormError("Общее количество страниц должно быть положительным числом.");
      return;
    }
    try {
      const created = await request("/books", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          author: author.trim() || null,
          pages_total: pagesTotalValue,
        }),
      });
      setItems((prev) => [created, ...prev]);
      setTitle("");
      setAuthor("");
      setPagesTotal("");
    } catch (err) {
      setFormError(getErrorMessage(err));
    }
  };

  const handleDelete = async (bookId) => {
    setError("");
    const confirmed = window.confirm(
      "Удалить книгу и все связанные данные?"
    );
    if (!confirmed) {
      return;
    }
    try {
      await request(`/books/${bookId}`, { method: "DELETE" });
      setItems((prev) => prev.filter((item) => item.id !== bookId));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Книги</h2>
            <p className="muted">Активные и архивные книги с прогрессом.</p>
          </div>
          <span className="badge">
            {loading ? "..." : `${items.length} книг`}
          </span>
        </div>
        {error && <div className="alert error">{error}</div>}
        {loading && <p className="muted">Загрузка списка...</p>}
        {!loading && items.length === 0 && (
          <div className="empty-state">Пока нет добавленных книг.</div>
        )}
        <div className="card-grid">
          {items.map((item, index) => (
            <div
              key={item.id}
              className="card book-card"
              style={{ "--delay": `${0.06 * index}s` }}
            >
              <div className="book-card-header">
                <div>
                  <div className="card-title">{item.title}</div>
                  <div className="card-meta">
                    {item.author ? item.author : "Автор не указан"}
                  </div>
                </div>
                <span
                  className={`pill status-pill ${
                    item.status === "archived"
                      ? "status-archived"
                      : "status-active"
                  }`}
                >
                  {item.status === "archived" ? "Архив" : "Активна"}
                </span>
              </div>
              <div className="book-stats">
                <div className="book-stat">
                  <div className="book-stat-label">Страницы</div>
                  <div className="book-stat-value">
                    {item.pages_total ?? "-"}
                  </div>
                </div>
                <div className="book-stat">
                  <div className="book-stat-label">Прочитано</div>
                  <div className="book-stat-value">
                    {item.pages_read_total ?? 0}
                  </div>
                </div>
                <div className="book-stat">
                  <div className="book-stat-label">Частей</div>
                  <div className="book-stat-value">{item.parts_total ?? 0}</div>
                </div>
                <div className="book-stat">
                  <div className="book-stat-label">Сессий</div>
                  <div className="book-stat-value">{item.sessions_total ?? 0}</div>
                </div>
                <div className="book-stat book-stat-wide">
                  <div className="book-stat-label">Время чтения</div>
                  <div className="book-stat-value">
                    {formatReadingDuration(item.reading_seconds_total)}
                  </div>
                </div>
              </div>
              <div className="form-actions">
                <button
                  className="danger-button"
                  type="button"
                  onClick={() => handleDelete(item.id)}
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Добавить книгу</h2>
            <p className="muted">Новая книга появится в списке слева.</p>
          </div>
        </div>
        <form className="form-inline" onSubmit={handleSubmit}>
          <div className="form-block">
            <label>Название</label>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Например, Clean Architecture"
            />
          </div>
          <div className="form-block">
            <label>Автор</label>
            <input
              value={author}
              onChange={(event) => setAuthor(event.target.value)}
              placeholder="Необязательно"
            />
          </div>
          <div className="form-block">
            <label>Всего страниц</label>
            <input
              type="number"
              value={pagesTotal}
              onChange={(event) => setPagesTotal(event.target.value)}
              placeholder="300"
              min="1"
            />
          </div>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Добавить книгу
            </button>
          </div>
        </form>
        {formError && <div className="alert error">{formError}</div>}
      </section>
    </div>
  );
};

export default Books;
