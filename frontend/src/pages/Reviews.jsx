import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const Reviews = () => {
  const [items, setItems] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await request("/reviews/today");
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

  const handleComplete = async (itemId) => {
    setActionError("");
    const answerText = answers[itemId] || "";
    try {
      await request(`/reviews/${itemId}/complete`, {
        method: "POST",
        body: JSON.stringify({ answers: { text: answerText } }),
      });
      setItems((prev) => prev.filter((item) => item.id !== itemId));
      setAnswers((prev) => ({ ...prev, [itemId]: "" }));
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Повторения</h2>
          <p className="muted">Сначала закрывайте короткие интервалы.</p>
        </div>
        <span className="badge">Сегодня</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      {actionError && <div className="alert error">{actionError}</div>}
      {loading && <p className="muted">Загрузка повторений...</p>}
      {!loading && items.length === 0 && (
        <div className="empty-state">На сегодня повторений нет.</div>
      )}
      <div className="review-grid">
        {items.map((item) => (
          <div key={item.id} className="review-card">
            <div className="review-header">
              <div>
                <div className="list-title">{item.book_title}</div>
                <div className="list-meta">
                  Часть {item.part_index} · Интервал {item.interval_days} дней
                </div>
              </div>
              <span className="pill">До {item.due_date}</span>
            </div>
            <div className="form-block full">
              <label>Ответ</label>
              <textarea
                rows="3"
                value={answers[item.id] || ""}
                onChange={(event) =>
                  setAnswers((prev) => ({
                    ...prev,
                    [item.id]: event.target.value,
                  }))
                }
                placeholder="Короткий ответ перед завершением"
              />
            </div>
            <div className="form-actions">
              <button
                className="primary-button"
                type="button"
                onClick={() => handleComplete(item.id)}
              >
                Завершить повторение
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default Reviews;
