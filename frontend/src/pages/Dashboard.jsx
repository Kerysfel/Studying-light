import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";
import { formatDueDate } from "../date.js";

const Dashboard = () => {
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showSummary, setShowSummary] = useState(
    () => sessionStorage.getItem("summaryDismissed") !== "true"
  );
  const [reviewsTab, setReviewsTab] = useState("today");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await request("/today");
      setToday(data);
      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const guardedLoad = async () => {
      if (!active) {
        return;
      }
      await load();
    };
    guardedLoad();
    const handleRefresh = () => {
      guardedLoad();
    };
    window.addEventListener("dashboard:refresh", handleRefresh);
    return () => {
      active = false;
      window.removeEventListener("dashboard:refresh", handleRefresh);
    };
  }, [load]);

  const activeBooks = today?.active_books || [];
  const reviewItems = today?.review_items || [];
  const overdueReviewItems = today?.overdue_review_items || [];
  const reviewProgress = today?.review_progress || { total: 0, completed: 0 };
  const reviewPercent = reviewProgress.total
    ? Math.min((reviewProgress.completed / reviewProgress.total) * 100, 100)
    : 0;
  const overdueCount = overdueReviewItems.length;
  const reviewBadgeLabel = overdueCount
    ? `${reviewItems.length} на сегодня · ${overdueCount} просрочено`
    : `${reviewItems.length} повторений`;
  const reviewSummaryLabel = overdueCount
    ? `Сегодня: ${reviewItems.length} · Просрочено: ${overdueCount}`
    : `Сегодня: ${reviewItems.length}`;
  const reviewTabItems = [
    {
      key: "today",
      label: `Сегодня (${reviewItems.length})`,
    },
    {
      key: "overdue",
      label: `Просроченные (${overdueCount})`,
      filled: overdueCount > 0,
    },
  ];
  const activeReviewItems =
    reviewsTab === "overdue" ? overdueReviewItems : reviewItems;
  const oldestOverdueDate = overdueReviewItems.reduce((oldest, item) => {
    if (!item?.due_date) {
      return oldest;
    }
    if (!oldest || item.due_date < oldest) {
      return item.due_date;
    }
    return oldest;
  }, null);
  const overdueMeta = overdueCount
    ? `Просрочено: ${overdueCount} · с ${formatDueDate(oldestOverdueDate, {
        todayLabel: "Сегодня",
      })}`
    : "Просроченных повторений нет";
  const overdueDetail = overdueCount
    ? "Начните с самых старых повторений."
    : "План без долгов, держим темп.";
  const summaryReviewItems = reviewItems.length
    ? reviewItems
    : overdueReviewItems;
  const summaryReviewEmpty =
    reviewItems.length === 0 && overdueReviewItems.length === 0;
  const emptyReviewLabel =
    reviewsTab === "overdue"
      ? "Просроченных повторений нет."
      : "На сегодня повторений нет.";
  const duePrefix = reviewsTab === "overdue" ? "Просрочено" : "До";

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
                    {reviewSummaryLabel}
                  </div>
                  {summaryReviewEmpty ? (
                    <div className="summary-muted">Повторений нет.</div>
                  ) : (
                    <>
                      {reviewItems.length === 0 && overdueReviewItems.length > 0 && (
                        <div className="summary-muted">
                          Есть просроченные повторения.
                        </div>
                      )}
                      <ul className="summary-list">
                        {summaryReviewItems.slice(0, 3).map((item) => (
                          <li key={item.id}>
                            {item.book_title} · Часть {item.part_index}
                          </li>
                        ))}
                      </ul>
                    </>
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
          <span className="badge">{reviewBadgeLabel}</span>
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
              meta: reviewSummaryLabel,
              detail: "Короткие интервалы даются легче всего.",
            },
            {
              title: "Просрочки",
              meta: overdueMeta,
              detail: overdueDetail,
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
          <div className="card" style={{ "--delay": `${0.05 * 3}s` }}>
            <div className="card-title">Прогресс повторений</div>
            <div className="card-meta">
              {reviewProgress.completed} / {reviewProgress.total} завершено
            </div>
            <div className="progress-track">
              <div className="progress-bar" style={{ width: `${reviewPercent}%` }} />
            </div>
          </div>
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
        <div className="tabs">
          {reviewTabItems.map((tab) => (
            <button
              key={tab.key}
              className={`tab-button${reviewsTab === tab.key ? " active" : ""}${
                tab.filled ? " filled" : ""
              }`}
              type="button"
              onClick={() => setReviewsTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="tab-panel">
          {loading && <p className="muted">Загрузка повторений...</p>}
          {!loading && activeReviewItems.length === 0 && (
            <div className="empty-state">{emptyReviewLabel}</div>
          )}
          {!loading && activeReviewItems.length > 0 && (
            <div className="list">
              {activeReviewItems.map((item) => (
                <div key={item.id} className="list-row">
                  <div>
                    <div className="list-title">{item.book_title}</div>
                    <div className="list-meta">
                      Часть {item.part_index} · Интервал {item.interval_days} дней
                      · {duePrefix}{" "}
                      {formatDueDate(item.due_date, { todayLabel: "Сегодня" })}
                    </div>
                  </div>
                  <Link className="primary-button" to="/reviews">
                    Начать повторение
                  </Link>
                </div>
              ))}
            </div>
          )}
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
              <div className="list-meta">
                {item.pages_total
                  ? `Страниц: ${item.pages_read_total} / ${item.pages_total}`
                  : "Страницы не указаны"}
              </div>
              {item.pages_total && (
                <div className="progress-track">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${Math.min(
                        (item.pages_read_total / item.pages_total) * 100,
                        100
                      )}%`,
                    }}
                  />
                </div>
              )}
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
