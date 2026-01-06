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
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Книги</h2>
          <p className="muted">Управляйте активными и архивными книгами.</p>
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
      {error && <div className="alert error">{error}</div>}
      {loading && <p className="muted">Загрузка списка...</p>}
      {!loading && items.length === 0 && (
        <div className="empty-state">Пока нет добавленных книг.</div>
      )}
      <div className="card-grid">
        {items.map((item, index) => (
          <div
            key={item.id}
            className="card"
            style={{ "--delay": `${0.06 * index}s` }}
          >
            <div className="card-title">{item.title}</div>
            <div className="card-meta">
              {item.status === "archived" ? "Архив" : "Активна"}
            </div>
            <div className="card-detail">
              {item.author ? `Автор: ${item.author}` : "Автор не указан"}
            </div>
            <div className="card-detail">
              {item.pages_total
                ? `Страниц: ${item.pages_total}`
                : "Страницы не указаны"}
            </div>
            <div className="card-detail">
              {`Прочитано страниц: ${item.pages_read_total ?? 0}`}
            </div>
            <div className="card-detail">
              {`Частей сохранено: ${item.parts_total ?? 0}`}
            </div>
            <div className="card-detail">
              {`Сессий чтения: ${item.sessions_total ?? 0}`}
            </div>
            <div className="card-detail">
              {`Время чтения: ${formatReadingDuration(item.reading_seconds_total)}`}
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
  );
};

export default Books;
