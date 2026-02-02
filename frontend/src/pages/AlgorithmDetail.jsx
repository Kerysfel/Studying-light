import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const AlgorithmDetail = () => {
  const { id } = useParams();
  const [algorithm, setAlgorithm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copyState, setCopyState] = useState({ id: null, message: "" });
  const [bookTitles, setBookTitles] = useState(new Map());

  useEffect(() => {
    let active = true;
    const loadAlgorithm = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await request(`/algorithms/${id}`);
        if (!active) {
          return;
        }
        setAlgorithm(data);
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
    loadAlgorithm();
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    let active = true;
    const loadBooks = async () => {
      if (!algorithm?.source_part?.book_id) {
        return;
      }
      try {
        const data = await request("/books");
        if (!active) {
          return;
        }
        const map = new Map();
        data.forEach((book) => {
          map.set(book.id, book.title);
        });
        setBookTitles(map);
      } catch (err) {
        if (!active) {
          return;
        }
        setBookTitles(new Map());
      }
    };
    loadBooks();
    return () => {
      active = false;
    };
  }, [algorithm]);

  const sourceInfo = useMemo(() => {
    if (!algorithm?.source_part) {
      return null;
    }
    const part = algorithm.source_part;
    const title = bookTitles.get(part.book_id);
    return {
      partIndex: part.part_index,
      bookTitle: title || `Книга #${part.book_id}`,
    };
  }, [algorithm, bookTitles]);

  const handleCopy = async (snippetId, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState({ id: snippetId, message: "Скопировано" });
      setTimeout(() => setCopyState({ id: null, message: "" }), 1500);
    } catch (err) {
      setCopyState({ id: snippetId, message: "Не удалось скопировать" });
      setTimeout(() => setCopyState({ id: null, message: "" }), 1500);
    }
  };

  if (loading) {
    return <p className="muted">Загрузка алгоритма...</p>;
  }

  if (error) {
    return <div className="alert error">{error}</div>;
  }

  if (!algorithm) {
    return null;
  }

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>{algorithm.title}</h2>
            <p className="muted">Детали алгоритма.</p>
          </div>
          <Link
            className="ghost-button"
            to={`/algorithm-groups/${algorithm.group_id}`}
          >
            К группе
          </Link>
        </div>

        {sourceInfo && (
          <div className="summary-block">
            <div className="summary-title">Источник</div>
            <div className="summary-value">
              <Link className="ghost-button" to="/books">
                Источник: часть {sourceInfo.partIndex} книги {sourceInfo.bookTitle}
              </Link>
            </div>
          </div>
        )}

        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-title">Сводка</div>
            <div className="summary-text">
              {algorithm.summary || "Сводка не найдена."}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Когда применять</div>
            <div className="summary-text">
              {algorithm.when_to_use || "-"}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Сложность</div>
            <div className="summary-text">
              {algorithm.complexity || "-"}
            </div>
          </div>
        </div>

        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-title">Инварианты</div>
            {algorithm.invariants?.length ? (
              <ul className="summary-list">
                {algorithm.invariants.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
          <div className="summary-card">
            <div className="summary-title">Шаги</div>
            {algorithm.steps?.length ? (
              <ul className="summary-list">
                {algorithm.steps.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
          <div className="summary-card">
            <div className="summary-title">Пограничные случаи</div>
            {algorithm.corner_cases?.length ? (
              <ul className="summary-list">
                {algorithm.corner_cases.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
        </div>

        <div className="summary-block">
          <div className="summary-title">Код</div>
          <div className="list">
            {(algorithm.code_snippets || []).map((snippet) => (
              <div key={snippet.id} className="code-snippet">
                <div className="code-snippet-header">
                  <div>
                    <div className="list-title">
                      {snippet.code_kind} · {snippet.language}
                    </div>
                    <div className="list-meta">
                      {snippet.is_reference ? "Референс" : "Заметка"}
                    </div>
                  </div>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleCopy(snippet.id, snippet.code_text)}
                  >
                    {copyState.id === snippet.id
                      ? copyState.message
                      : "Copy"}
                  </button>
                </div>
                <pre className="code-area">
                  <code>{snippet.code_text}</code>
                </pre>
              </div>
            ))}
            {!algorithm.code_snippets?.length && (
              <div className="summary-text">Код отсутствует.</div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

export default AlgorithmDetail;
