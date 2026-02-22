import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  PERFORMANCE_SORT_OPTIONS,
  SORT_DIRECTION_OPTIONS,
  buildQueryString,
  dateDaysAgo,
  formatDuration,
  formatRating,
  formatScore,
  parseInteger,
  toIsoDate,
} from "../adminPerformance.js";
import { request } from "../api.js";
import ErrorBanner from "../components/ErrorBanner.jsx";
import AdminPagination from "../components/AdminPagination.jsx";
import { formatDateTime } from "../date.js";

const DEFAULT_LIMIT = 20;

const normalizeLimit = (value) => {
  const parsed = parseInteger(value, DEFAULT_LIMIT);
  if (parsed <= 0) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, 200);
};

const AdminPerformance = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const appliedSearch = searchParams.get("search") || "";
  const appliedDateFrom = searchParams.get("date_from") || "";
  const appliedDateTo = searchParams.get("date_to") || "";
  const appliedSortBy = searchParams.get("sort_by") || "last_activity_at";
  const appliedSortDir = searchParams.get("sort_dir") || "desc";
  const appliedLimit = normalizeLimit(searchParams.get("limit"));
  const appliedOffset = parseInteger(searchParams.get("offset"), 0);

  const [searchInput, setSearchInput] = useState(appliedSearch);
  const [dateFromInput, setDateFromInput] = useState(appliedDateFrom);
  const [dateToInput, setDateToInput] = useState(appliedDateTo);
  const [sortByInput, setSortByInput] = useState(appliedSortBy);
  const [sortDirInput, setSortDirInput] = useState(appliedSortDir);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setSearchInput(appliedSearch);
    setDateFromInput(appliedDateFrom);
    setDateToInput(appliedDateTo);
    setSortByInput(appliedSortBy);
    setSortDirInput(appliedSortDir);
  }, [appliedSearch, appliedDateFrom, appliedDateTo, appliedSortBy, appliedSortDir]);

  const appliedQuery = useMemo(
    () =>
      buildQueryString({
        search: appliedSearch,
        date_from: appliedDateFrom,
        date_to: appliedDateTo,
        sort_by: appliedSortBy,
        sort_dir: appliedSortDir,
        limit: appliedLimit,
        offset: appliedOffset,
      }),
    [
      appliedSearch,
      appliedDateFrom,
      appliedDateTo,
      appliedSortBy,
      appliedSortDir,
      appliedLimit,
      appliedOffset,
    ]
  );

  const updateParams = (patch) => {
    const next = new URLSearchParams(searchParams);

    Object.entries(patch).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") {
        next.delete(key);
        return;
      }
      next.set(key, String(value));
    });

    setSearchParams(next);
  };

  const applyFilters = () => {
    updateParams({
      search: searchInput.trim(),
      date_from: dateFromInput,
      date_to: dateToInput,
      sort_by: sortByInput,
      sort_dir: sortDirInput,
      limit: appliedLimit,
      offset: 0,
    });
  };

  const resetFilters = () => {
    setSearchParams(new URLSearchParams({ sort_by: "last_activity_at", sort_dir: "desc" }));
  };

  const applyQuickPeriod = (days) => {
    if (days === null) {
      updateParams({ date_from: null, date_to: null, offset: 0 });
      return;
    }
    updateParams({
      date_from: dateDaysAgo(days - 1),
      date_to: toIsoDate(new Date()),
      offset: 0,
    });
  };

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const path = appliedQuery
          ? `/admin/users/performance?${appliedQuery}`
          : "/admin/users/performance";
        const response = await request(path);
        if (!cancelled) {
          setItems(Array.isArray(response?.items) ? response.items : []);
          setTotal(Number(response?.total || 0));
        }
      } catch (requestError) {
        if (!cancelled) {
          setError({
            detail: requestError?.detail || "Не удалось загрузить успеваемость пользователей",
            code: requestError?.code || "UNKNOWN",
            errors: requestError?.errors || null,
          });
          setItems([]);
          setTotal(0);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [appliedQuery]);

  const countLabel = useMemo(() => {
    if (loading) {
      return "Загрузка...";
    }
    return `Пользователей: ${total}`;
  }, [loading, total]);

  const handleLimitChange = (event) => {
    const nextLimit = normalizeLimit(event.target.value);
    updateParams({ limit: nextLimit, offset: 0 });
  };

  const goToPageOffset = (nextOffset) => {
    updateParams({ offset: Math.max(0, nextOffset) });
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Успеваемость пользователей</h2>
          <p className="muted">{countLabel}</p>
        </div>
      </div>

      <ErrorBanner error={error} />

      <div className="admin-filters performance-filters">
        <div className="form-block">
          <label htmlFor="performance-search">Поиск</label>
          <input
            id="performance-search"
            type="search"
            placeholder="email"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>

        <div className="form-block">
          <label htmlFor="performance-date-from">Дата с</label>
          <input
            id="performance-date-from"
            type="date"
            value={dateFromInput}
            onChange={(event) => setDateFromInput(event.target.value)}
          />
        </div>

        <div className="form-block">
          <label htmlFor="performance-date-to">Дата по</label>
          <input
            id="performance-date-to"
            type="date"
            value={dateToInput}
            onChange={(event) => setDateToInput(event.target.value)}
          />
        </div>

        <div className="form-block">
          <label htmlFor="performance-sort-by">Сортировка</label>
          <select
            id="performance-sort-by"
            value={sortByInput}
            onChange={(event) => setSortByInput(event.target.value)}
          >
            {PERFORMANCE_SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-block">
          <label htmlFor="performance-sort-dir">Направление</label>
          <select
            id="performance-sort-dir"
            value={sortDirInput}
            onChange={(event) => setSortDirInput(event.target.value)}
          >
            {SORT_DIRECTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-block">
          <label htmlFor="performance-limit">На страницу</label>
          <select
            id="performance-limit"
            value={String(appliedLimit)}
            onChange={handleLimitChange}
          >
            {[20, 50, 100].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="performance-filter-actions">
        <button type="button" className="primary-button" onClick={applyFilters}>
          Применить
        </button>
        <button type="button" className="ghost-button" onClick={resetFilters}>
          Сбросить
        </button>
      </div>
      <div className="performance-quick-filters">
        <button
          type="button"
          className="ghost-button"
          onClick={() => applyQuickPeriod(7)}
        >
          7 дней
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={() => applyQuickPeriod(30)}
        >
          30 дней
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={() => applyQuickPeriod(90)}
        >
          90 дней
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={() => applyQuickPeriod(null)}
        >
          Все
        </button>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table performance-table">
          <thead>
            <tr>
              <th>Пользователь</th>
              <th>Последняя активность</th>
              <th>Всего</th>
              <th>Чтение</th>
              <th>Теория</th>
              <th>Алгоритмы</th>
              <th>Typing</th>
              <th>Memory</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9}>
                  <div className="admin-skeleton" />
                </td>
              </tr>
            )}

            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={9} className="admin-empty">
                  Нет данных по выбранным фильтрам.
                </td>
              </tr>
            )}

            {!loading &&
              items.map((item) => {
                const detailQuery = buildQueryString({
                  date_from: appliedDateFrom,
                  date_to: appliedDateTo,
                  back: appliedQuery,
                });
                const detailTo = detailQuery
                  ? `/admin/performance/${item.user_id}?${detailQuery}`
                  : `/admin/performance/${item.user_id}`;

                return (
                  <tr key={item.user_id}>
                    <td>
                      <div className="performance-cell-stack">
                        <strong>{item.email}</strong>
                        {item.name && <span className="muted">{item.name}</span>}
                      </div>
                    </td>
                    <td>{formatDateTime(item.last_activity_at)}</td>
                    <td>{item.total_activity_count}</td>
                    <td>
                      <div className="performance-cell-stack">
                        <span>{item.reading_sessions_count} сессий</span>
                        <span className="muted">{formatDuration(item.reading_total_duration_sec)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="performance-cell-stack">
                        <span>{item.review_theory_count} попыток</span>
                        <span className="muted">
                          R: {formatRating(item.review_theory_avg_rating)} / S: {formatScore(item.review_theory_avg_score)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="performance-cell-stack">
                        <span>{item.review_algorithm_theory_count} попыток</span>
                        <span className="muted">R: {formatRating(item.review_algorithm_theory_avg_rating)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="performance-cell-stack">
                        <span>{item.training_typing_count} попыток</span>
                        <span className="muted">
                          {formatDuration(item.training_typing_total_duration_sec)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="performance-cell-stack">
                        <span>{item.training_memory_count} попыток</span>
                        <span className="muted">
                          {formatDuration(item.training_memory_total_duration_sec)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <Link to={detailTo} className="ghost-button admin-action-button">
                        Подробнее
                      </Link>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      <AdminPagination
        total={total}
        limit={appliedLimit}
        offset={appliedOffset}
        onChange={goToPageOffset}
      />
    </section>
  );
};

export default AdminPerformance;
