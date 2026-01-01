import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const splitLines = (value) =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

const parseTerms = (value) =>
  splitLines(value)
    .map((line) => {
      const separator = line.includes("—")
        ? "—"
        : line.includes(":")
        ? ":"
        : "-";
      const [term, ...rest] = line.split(separator);
      const definition = rest.join(separator).trim();
      return {
        term: term.trim(),
        definition: definition || null,
      };
    })
    .filter((item) => item.term);

const ReadingSession = () => {
  const [books, setBooks] = useState([]);
  const [selectedBook, setSelectedBook] = useState("");
  const [label, setLabel] = useState("");
  const [keywords, setKeywords] = useState("");
  const [terms, setTerms] = useState("");
  const [sentences, setSentences] = useState("");
  const [freeform, setFreeform] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [createdPart, setCreatedPart] = useState(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await request("/books");
        if (!active) {
          return;
        }
        setBooks(data);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  const activeBooks = useMemo(
    () => books.filter((book) => book.status !== "archived"),
    [books]
  );

  const handleCloseSession = async () => {
    setError("");
    if (!selectedBook) {
      setError("Выберите книгу для сессии.");
      return;
    }

    const payload = {
      book_id: Number(selectedBook),
      label: label.trim() || null,
      raw_notes: {
        keywords: keywords
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        terms: parseTerms(terms),
        sentences: splitLines(sentences),
        freeform: splitLines(freeform),
      },
    };

    try {
      setSaving(true);
      const part = await request("/parts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setCreatedPart(part);
      localStorage.setItem("lastPartId", String(part.id));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Сессия чтения</h2>
            <p className="muted">Одна глава, одна чистая часть.</p>
          </div>
          <span className="badge">Помодоро</span>
        </div>
        <div className="timer-card">
          <div className="timer-count">00:25:00</div>
          <div className="timer-meta">Рабочий цикл 1 из 4</div>
          <div className="timer-actions">
            <button className="primary-button" type="button">
              Старт
            </button>
            <button className="ghost-button" type="button">
              Сброс
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Часть и заметки</h2>
            <p className="muted">Сохраняйте результат сессии сразу.</p>
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-grid">
          <div className="form-block">
            <label>Книга</label>
            <select
              value={selectedBook}
              onChange={(event) => setSelectedBook(event.target.value)}
            >
              <option value="">Выберите книгу</option>
              {activeBooks.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.title}
                </option>
              ))}
            </select>
            {activeBooks.length === 0 && (
              <div className="empty-state">
                Нет активных книг. Добавьте книгу перед сессией.
                <Link className="inline-link" to="/books">
                  Перейти к книгам
                </Link>
              </div>
            )}
          </div>
          <div className="form-block">
            <label>Метка части</label>
            <input
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="Например, Гл. 3-4"
            />
          </div>
          <div className="form-block">
            <label>Ключевые слова</label>
            <input
              value={keywords}
              onChange={(event) => setKeywords(event.target.value)}
              placeholder="слово, слово"
            />
          </div>
          <div className="form-block">
            <label>Термины (каждый с новой строки)</label>
            <textarea
              rows="3"
              value={terms}
              onChange={(event) => setTerms(event.target.value)}
              placeholder={"Термин — определение"}
            />
          </div>
          <div className="form-block full">
            <label>Важные предложения</label>
            <textarea
              rows="3"
              value={sentences}
              onChange={(event) => setSentences(event.target.value)}
              placeholder="Одно предложение в строке"
            />
          </div>
          <div className="form-block full">
            <label>Свободные заметки</label>
            <textarea
              rows="3"
              value={freeform}
              onChange={(event) => setFreeform(event.target.value)}
              placeholder="Короткие пункты или фразы"
            />
          </div>
        </div>
        <div className="form-actions">
          <button className="ghost-button" type="button">
            Сгенерировать промпт
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={handleCloseSession}
            disabled={saving}
          >
            {saving ? "Сохранение..." : "Закрыть сессию"}
          </button>
        </div>
        {createdPart && (
          <div className="success-block">
            <div className="success-title">Часть сохранена</div>
            <div className="success-detail">
              Часть #{createdPart.part_index} добавлена. Продолжите импорт JSON.
            </div>
            <Link className="primary-button" to="/import">
              Перейти к импорту
            </Link>
          </div>
        )}
      </section>
    </div>
  );
};

export default ReadingSession;
