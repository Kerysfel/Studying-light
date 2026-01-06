import { useEffect, useMemo, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const summarize = (text) => {
  if (!text) {
    return "Краткое содержание недоступно.";
  }
  const words = text.trim().split(/\s+/).slice(0, 10);
  return words.join(" ") + (words.length === 10 ? "..." : "");
};

const formatDate = (value) => {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
};

const ImportExport = () => {
  const [books, setBooks] = useState([]);
  const [parts, setParts] = useState([]);
  const [selectedBookId, setSelectedBookId] = useState("");
  const [selectedPartId, setSelectedPartId] = useState("");
  const [payload, setPayload] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingParts, setLoadingParts] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    const loadBooks = async () => {
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
    loadBooks();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const loadParts = async () => {
      if (!selectedBookId) {
        setParts([]);
        setSelectedPartId("");
        return;
      }
      try {
        setLoadingParts(true);
        const data = await request(`/parts?book_id=${selectedBookId}`);
        if (!active) {
          return;
        }
        setParts(data);
        setError("");
        const stored = localStorage.getItem("lastPartId");
        if (stored && data.some((item) => String(item.id) === stored)) {
          setSelectedPartId(stored);
        }
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      } finally {
        if (active) {
          setLoadingParts(false);
        }
      }
    };
    loadParts();
    return () => {
      active = false;
    };
  }, [selectedBookId]);

  useEffect(() => {
    if (selectedPartId) {
      localStorage.setItem("lastPartId", selectedPartId);
    }
  }, [selectedPartId]);

  const selectedPart = useMemo(
    () => parts.find((item) => String(item.id) === selectedPartId) || null,
    [parts, selectedPartId]
  );

  const handleImport = async () => {
    setError("");
    setSuccess("");
    if (!selectedBookId) {
      setError("Сначала выберите книгу.");
      return;
    }
    if (!selectedPartId) {
      setError("Выберите часть для импорта.");
      return;
    }
    if (!payload.trim()) {
      setError("Вставьте JSON для импорта.");
      return;
    }

    let data;
    try {
      data = JSON.parse(payload);
    } catch (err) {
      setError("Некорректный JSON. Проверьте формат.");
      return;
    }

    try {
      setLoading(true);
      const response = await request(`/parts/${selectedPartId}/import_gpt`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      const count = response.review_items?.length || 0;
      setSuccess(`Импорт завершен. Создано повторений: ${count}.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Импорт JSON</h2>
            <p className="muted">Вставьте ответ от ChatGPT.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block">
            <label>Книга</label>
            <select
              value={selectedBookId}
              onChange={(event) => setSelectedBookId(event.target.value)}
            >
              <option value="">Выберите книгу</option>
              {books.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.title}
                </option>
              ))}
            </select>
          </div>
          <div className="form-block">
            <label>Часть</label>
            <select
              value={selectedPartId}
              onChange={(event) => setSelectedPartId(event.target.value)}
              disabled={!selectedBookId || loadingParts}
            >
              <option value="">Выберите часть</option>
              {parts.map((part) => (
                <option key={part.id} value={part.id}>
                  Часть {part.part_index} - {formatDate(part.created_at)}
                </option>
              ))}
            </select>
          </div>
          {selectedPart && (
            <div className="form-block full">
              <label>Детали выбранной части</label>
              <div className="card">
                <div className="card-title">
                  Часть {selectedPart.part_index}
                </div>
                <div className="card-meta">
                  Создано: {formatDate(selectedPart.created_at)}
                </div>
                <div className="card-detail">{summarize(selectedPart.gpt_summary)}</div>
              </div>
            </div>
          )}
          <div className="form-block full">
            <label>JSON</label>
            <textarea
              rows="8"
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              placeholder='{"gpt_summary": "...", "gpt_questions_by_interval": {...}}'
            />
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        <div className="form-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleImport}
            disabled={loading}
          >
            {loading ? "Импорт..." : "Импортировать"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Экспорт</h2>
            <p className="muted">Скачайте данные в формате JSON.</p>
          </div>
        </div>
        <button className="ghost-button" type="button">
          Экспорт JSON
        </button>
      </section>
    </div>
  );
};

export default ImportExport;
