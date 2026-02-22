import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  ACTIVITY_KIND_OPTIONS,
  buildEntityPresentation,
  buildQueryString,
  dateDaysAgo,
  formatAccuracy,
  formatActivityKind,
  formatActivitySource,
  formatActivityStatus,
  formatDuration,
  formatRating,
  formatScore,
  parseInteger,
  toIsoDate,
} from "../adminPerformance.js";
import { request } from "../api.js";
import AdminPagination from "../components/AdminPagination.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { formatDateTime } from "../date.js";

const DEFAULT_ACTIVITY_LIMIT = 25;

const normalizeLimit = (value) => {
  const parsed = parseInteger(value, DEFAULT_ACTIVITY_LIMIT);
  if (parsed <= 0) {
    return DEFAULT_ACTIVITY_LIMIT;
  }
  return Math.min(parsed, 500);
};

const MetricRow = ({ label, value }) => {
  return (
    <div className="performance-metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
};

const SummaryCard = ({ title, subtitle, children }) => {
  return (
    <article className="performance-summary-card">
      <div className="performance-summary-header">
        <h3>{title}</h3>
        {subtitle && <p>{subtitle}</p>}
      </div>
      <div className="performance-metric-list">{children}</div>
    </article>
  );
};

const AdminPerformanceUser = () => {
  const { userId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const appliedDateFrom = searchParams.get("date_from") || "";
  const appliedDateTo = searchParams.get("date_to") || "";
  const appliedActivityKind = searchParams.get("activity_kind") || "all";
  const appliedLimit = normalizeLimit(searchParams.get("limit"));
  const appliedOffset = parseInteger(searchParams.get("offset"), 0);
  const backQuery = searchParams.get("back") || "";

  const [dateFromInput, setDateFromInput] = useState(appliedDateFrom);
  const [dateToInput, setDateToInput] = useState(appliedDateTo);

  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);

  const [activities, setActivities] = useState([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activitiesLoading, setActivitiesLoading] = useState(true);
  const [activitiesError, setActivitiesError] = useState(null);

  useEffect(() => {
    setDateFromInput(appliedDateFrom);
    setDateToInput(appliedDateTo);
  }, [appliedDateFrom, appliedDateTo]);

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

  const baseQuery = useMemo(
    () =>
      buildQueryString({
        date_from: appliedDateFrom,
        date_to: appliedDateTo,
      }),
    [appliedDateFrom, appliedDateTo]
  );

  const activityQuery = useMemo(
    () =>
      buildQueryString({
        date_from: appliedDateFrom,
        date_to: appliedDateTo,
        activity_kind: appliedActivityKind,
        limit: appliedLimit,
        offset: appliedOffset,
      }),
    [appliedDateFrom, appliedDateTo, appliedActivityKind, appliedLimit, appliedOffset]
  );

  useEffect(() => {
    let cancelled = false;

    const loadSummary = async () => {
      setSummaryLoading(true);
      setSummaryError(null);
      try {
        const path = baseQuery
          ? `/admin/users/${userId}/performance?${baseQuery}`
          : `/admin/users/${userId}/performance`;
        const data = await request(path);
        if (!cancelled) {
          setSummary(data);
        }
      } catch (requestError) {
        if (!cancelled) {
          setSummaryError({
            detail: requestError?.detail || "Не удалось загрузить карточку пользователя",
            code: requestError?.code || "UNKNOWN",
            errors: requestError?.errors || null,
          });
          setSummary(null);
        }
      } finally {
        if (!cancelled) {
          setSummaryLoading(false);
        }
      }
    };

    loadSummary();

    return () => {
      cancelled = true;
    };
  }, [userId, baseQuery]);

  useEffect(() => {
    let cancelled = false;

    const loadActivities = async () => {
      setActivitiesLoading(true);
      setActivitiesError(null);
      try {
        const path = activityQuery
          ? `/admin/users/${userId}/activities?${activityQuery}`
          : `/admin/users/${userId}/activities`;
        const data = await request(path);
        if (!cancelled) {
          setActivities(Array.isArray(data?.items) ? data.items : []);
          setActivityTotal(Number(data?.total || 0));
        }
      } catch (requestError) {
        if (!cancelled) {
          setActivitiesError({
            detail: requestError?.detail || "Не удалось загрузить ленту активностей",
            code: requestError?.code || "UNKNOWN",
            errors: requestError?.errors || null,
          });
          setActivities([]);
          setActivityTotal(0);
        }
      } finally {
        if (!cancelled) {
          setActivitiesLoading(false);
        }
      }
    };

    loadActivities();

    return () => {
      cancelled = true;
    };
  }, [userId, activityQuery]);

  const applyDateFilter = () => {
    updateParams({
      date_from: dateFromInput,
      date_to: dateToInput,
      offset: 0,
    });
  };

  const resetDateFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("date_from");
    next.delete("date_to");
    next.set("offset", "0");
    setSearchParams(next);
  };

  const setActivityKind = (kind) => {
    updateParams({
      activity_kind: kind,
      offset: 0,
    });
  };

  const setPageOffset = (nextOffset) => {
    updateParams({ offset: Math.max(0, nextOffset) });
  };

  const setPageLimit = (event) => {
    updateParams({
      limit: normalizeLimit(event.target.value),
      offset: 0,
    });
  };

  const backHref = backQuery ? `/admin/performance?${backQuery}` : "/admin/performance";
  const userLabel = summary?.name ? `${summary.email} (${summary.name})` : summary?.email || userId;
  const periodLabel = appliedDateFrom || appliedDateTo
    ? `${appliedDateFrom || "…"} - ${appliedDateTo || "…"}`
    : "за все время";

  const applyQuickPeriod = (days) => {
    if (days === null) {
      updateParams({
        date_from: null,
        date_to: null,
        offset: 0,
      });
      return;
    }
    updateParams({
      date_from: dateDaysAgo(days - 1),
      date_to: toIsoDate(new Date()),
      offset: 0,
    });
  };

  return (
    <>
      <section className="panel">
        <div className="panel-header performance-header">
          <div>
            <h2>Профиль успеваемости</h2>
            <p className="muted">{userLabel}</p>
            {!summaryLoading && summary && (
              <p className="muted">
                Последняя активность: {formatDateTime(summary.last_activity_at)} · Всего событий: {summary.total_activity_count}
              </p>
            )}
            <p className="muted">Период: {periodLabel}</p>
          </div>
          <Link to={backHref} className="ghost-button performance-back-button">
            Назад к списку
          </Link>
        </div>

        <ErrorBanner error={summaryError} />

        <div className="admin-filters performance-filters">
          <div className="form-block">
            <label htmlFor="user-performance-date-from">Дата с</label>
            <input
              id="user-performance-date-from"
              type="date"
              value={dateFromInput}
              onChange={(event) => setDateFromInput(event.target.value)}
            />
          </div>
          <div className="form-block">
            <label htmlFor="user-performance-date-to">Дата по</label>
            <input
              id="user-performance-date-to"
              type="date"
              value={dateToInput}
              onChange={(event) => setDateToInput(event.target.value)}
            />
          </div>
        </div>

        <div className="performance-filter-actions">
          <button type="button" className="primary-button" onClick={applyDateFilter}>
            Применить период
          </button>
          <button type="button" className="ghost-button" onClick={resetDateFilter}>
            Сбросить период
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

        {summaryLoading && (
          <div className="performance-summary-grid">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="performance-summary-card">
                <div className="admin-skeleton" />
              </div>
            ))}
          </div>
        )}

        {!summaryLoading && summary && (
          <div className="performance-summary-grid">
            <SummaryCard title="Чтение" subtitle="за выбранный период">
              <MetricRow label="Сессий" value={summary.reading.sessions_count} />
              <MetricRow
                label="Общее время"
                value={formatDuration(summary.reading.total_duration_sec)}
              />
              <MetricRow
                label="Средняя длительность"
                value={formatDuration(summary.reading.avg_duration_sec)}
              />
            </SummaryCard>

            <SummaryCard title="Повторения (теория)" subtitle="за выбранный период">
              <MetricRow label="Попыток" value={summary.review_theory.attempts_count} />
              <MetricRow
                label="Средний rating"
                value={formatRating(summary.review_theory.avg_rating)}
              />
              <MetricRow
                label="Средний score"
                value={formatScore(summary.review_theory.avg_score)}
              />
              <MetricRow
                label="Последний rating"
                value={formatRating(summary.review_theory.last_rating)}
              />
              <MetricRow
                label="Последний score"
                value={formatScore(summary.review_theory.last_score)}
              />
            </SummaryCard>

            <SummaryCard title="Повторения (алгоритмы)" subtitle="за выбранный период">
              <MetricRow
                label="Попыток"
                value={summary.review_algorithm_theory.attempts_count}
              />
              <MetricRow
                label="Средний rating"
                value={formatRating(summary.review_algorithm_theory.avg_rating)}
              />
              <MetricRow
                label="Последний rating"
                value={formatRating(summary.review_algorithm_theory.last_rating)}
              />
            </SummaryCard>

            <SummaryCard title="Typing" subtitle="за выбранный период">
              <MetricRow label="Попыток" value={summary.training_typing.attempts_count} />
              <MetricRow
                label="Общее время"
                value={formatDuration(summary.training_typing.total_duration_sec)}
              />
              <MetricRow
                label="Средняя длительность"
                value={formatDuration(summary.training_typing.avg_duration_sec)}
              />
              <MetricRow
                label="Средняя accuracy"
                value={formatAccuracy(summary.training_typing.avg_accuracy)}
              />
              <MetricRow
                label="Средний rating"
                value={formatRating(summary.training_typing.avg_rating)}
              />
            </SummaryCard>

            <SummaryCard title="Memory" subtitle="за выбранный период">
              <MetricRow label="Попыток" value={summary.training_memory.attempts_count} />
              <MetricRow
                label="Общее время"
                value={formatDuration(summary.training_memory.total_duration_sec)}
              />
              <MetricRow
                label="Средняя длительность"
                value={formatDuration(summary.training_memory.avg_duration_sec)}
              />
              <MetricRow
                label="Средний rating"
                value={formatRating(summary.training_memory.avg_rating)}
              />
            </SummaryCard>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Лента активностей</h2>
            <p className="muted">Событий: {activitiesLoading ? "..." : activityTotal}</p>
          </div>
          <div className="form-block performance-limit-picker">
            <label htmlFor="user-activities-limit">На страницу</label>
            <select
              id="user-activities-limit"
              value={String(appliedLimit)}
              onChange={setPageLimit}
            >
              {[25, 50, 100].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="tabs">
          {ACTIVITY_KIND_OPTIONS.map((option) => {
            const active = appliedActivityKind === option.value;
            return (
              <button
                key={option.value}
                type="button"
                className={`tab-button${active ? " active" : ""}`}
                onClick={() => setActivityKind(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        <ErrorBanner error={activitiesError} />

        <div className="admin-table-wrap performance-activities-wrap">
          <table className="admin-table performance-activities-table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Тип</th>
                <th>Сущность</th>
                <th>Длительность</th>
                <th>Результат</th>
                <th>Статус</th>
                <th>Источник</th>
              </tr>
            </thead>
            <tbody>
              {activitiesLoading && (
                <tr>
                  <td colSpan={8}>
                    <div className="admin-skeleton" />
                  </td>
                </tr>
              )}

              {!activitiesLoading && activities.length === 0 && (
                <tr>
                  <td colSpan={8} className="admin-empty">
                    Активности по текущему фильтру отсутствуют.
                  </td>
                </tr>
              )}

              {!activitiesLoading &&
                activities.map((event) => {
                  const entity = buildEntityPresentation(event);
                  return (
                    <tr key={event.id}>
                      <td>{formatDateTime(event.ended_at || event.created_at)}</td>
                      <td>
                        <div className="performance-cell-stack">
                          <span>{formatActivityKind(event.activity_kind)}</span>
                          {event.result_label && (
                            <span className="muted">{event.result_label}</span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="performance-entity">
                          <strong title={entity.primary}>{entity.primary}</strong>
                          {entity.secondary && (
                            <span className="muted" title={entity.secondary}>
                              {entity.secondary}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>{formatDuration(event.duration_sec)}</td>
                      <td>
                        <div className="performance-cell-stack">
                          <span>R: {formatRating(event.rating_1_to_5)}</span>
                          <span>S: {formatScore(event.score_0_to_100)}</span>
                          <span>A: {formatAccuracy(event.accuracy)}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`activity-pill status-${event.status}`}>
                          {formatActivityStatus(event.status)}
                        </span>
                      </td>
                      <td>
                        <span className={`activity-pill source-${event.source}`}>
                          {formatActivitySource(event.source)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>

        <AdminPagination
          total={activityTotal}
          limit={appliedLimit}
          offset={appliedOffset}
          onChange={setPageOffset}
        />
      </section>
    </>
  );
};

export default AdminPerformanceUser;
