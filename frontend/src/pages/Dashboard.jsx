import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const Dashboard = () => {
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showSummary, setShowSummary] = useState(
    () => sessionStorage.getItem("summaryDismissed") !== "true"
  );

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await request("/today");
        if (!active) {
          return;
        }
        setToday(data);
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

  const activeBooks = today?.active_books || [];
  const reviewItems = today?.review_items || [];

  const dismissSummary = () => {
    setShowSummary(false);
    sessionStorage.setItem("summaryDismissed", "true");
  };

  return (
    <div className="page-grid">
      {showSummary && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div>
                <h2>Сводка на сегодня</h2>
                <p className="muted">
                  План чтения и повторений на ближайшие часы.
                </p>
              </div>
              <button className="ghost-button" type="button" onClick={dismissSummary}>
                Закрыть
              </button>
            </div>
            {loading ? (
              <p className="muted">Загрузка данных...</p>
            ) : error ? (
              <div className="alert error">{error}</div>
            ) : (
              <div className="summary-grid">
                <div className="summary-block">
                  <div className="summary-title">Сессии чтения</div>
                  <div className="summary-value">
                    Активные книги: {activeBooks.length}
                  </div>
                  {activeBooks.length === 0 ? (
                    <div className="summary-muted">Нет активных книг.</div>
                  ) : (
                    <ul className="summary-list">
                      {activeBooks.map((book) => (
                        <li key={book.id}>{book.title}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="summary-block">
                  <div className="summary-title">Повторения</div>
                  <div className="summary-value">
                    Запланировано: {reviewItems.length}
                  </div>
                  {reviewItems.length === 0 ? (
                    <div className="summary-muted">Повторений нет.</div>
                  ) : (
                    <ul className="summary-list">
                      {reviewItems.slice(0, 3).map((item) => (
                        <li key={item.id}>
                          {item.book_title} · Часть {item.part_index}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Сегодня в фокусе</h2>
            <p className="muted">
              Держите план компактным. Сначала закрывайте главное.
            </p>
          </div>
          <span className="badge">{reviewItems.length} повторений</span>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="card-grid">
          {[
            {
              title: "Сессия чтения",
              meta: `Активных книг: ${activeBooks.length}`,
              detail: "Начните с активной книги и закройте одну часть.",
            },
            {
              title: "Повторения",
              meta: `Запланировано: ${reviewItems.length}`,
              detail: "Короткие интервалы даются легче всего.",
            },
            {
              title: "Фокус",
              meta: "Один контекст",
              detail: "Короткие заметки и ясные выводы.",
            },
          ].map((item, index) => (
            <div
              key={item.title}
              className="card"
              style={{ "--delay": `${0.05 * index}s` }}
            >
              <div className="card-title">{item.title}</div>
              <div className="card-meta">{item.meta}</div>
              <p className="card-detail">{item.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Повторения на сегодня</h2>
            <p className="muted">Короткие интервалы закрываются быстрее.</p>
          </div>
          <Link className="ghost-button" to="/reviews">
            Все повторения
          </Link>
        </div>
        {loading && <p className="muted">Загрузка повторений...</p>}
        {!loading && reviewItems.length === 0 && (
          <div className="empty-state">На сегодня повторений нет.</div>
        )}
        <div className="list">
          {reviewItems.map((item) => (
            <div key={item.id} className="list-row">
              <div>
                <div className="list-title">{item.book_title}</div>
                <div className="list-meta">
                  Часть {item.part_index} · Интервал {item.interval_days} дней ·
                  До {item.due_date}
                </div>
              </div>
              <Link className="primary-button" to="/reviews">
                Начать повторение
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Очередь чтения</h2>
            <p className="muted">Активные книги готовы для новой части.</p>
          </div>
          <Link className="ghost-button" to="/books">
            Управлять книгами
          </Link>
        </div>
        {loading && <p className="muted">Загрузка списка...</p>}
        {!loading && activeBooks.length === 0 && (
          <div className="empty-state">Добавьте первую книгу.</div>
        )}
        <div className="list">
          {activeBooks.map((item) => (
            <div key={item.id} className="list-row">
              <div>
                <div className="list-title">{item.title}</div>
                <div className="list-meta">Готово к новой части</div>
              </div>
              <Link className="primary-button" to="/session">
                Начать сессию
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
