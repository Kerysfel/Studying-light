import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const Books = () => {
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
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
      setFormError("Введите название книги.");
      return;
    }
    try {
      const created = await request("/books", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), author: author.trim() || null }),
      });
      setItems((prev) => [created, ...prev]);
      setTitle("");
      setAuthor("");
    } catch (err) {
      setFormError(getErrorMessage(err));
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
          </div>
        ))}
      </div>
    </section>
  );
};

export default Books;
