import { useEffect, useMemo, useState } from "react";

import { request } from "../api.js";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { formatDateTime } from "../date.js";

const STATUS_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
];

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const buildUsersPath = ({ query, status }) => {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("query", query.trim());
  }
  if (status !== "all") {
    params.set("status", status);
  }
  const queryString = params.toString();
  return queryString ? `/admin/users?${queryString}` : "/admin/users";
};

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [actionUserId, setActionUserId] = useState(null);
  const [deactivateCandidate, setDeactivateCandidate] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(queryInput);
    }, 400);
    return () => clearTimeout(timer);
  }, [queryInput]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await request(buildUsersPath({ query, status }));
        if (!cancelled) {
          setUsers(Array.isArray(data) ? data : []);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError({
            detail: requestError?.detail || "Не удалось загрузить пользователей",
            code: requestError?.code || "UNKNOWN",
            errors: requestError?.errors || null,
          });
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
  }, [query, status]);

  const usersCountLabel = useMemo(() => {
    if (loading) {
      return "Загрузка...";
    }
    return `Найдено: ${users.length}`;
  }, [loading, users.length]);

  const toggleActive = async (user) => {
    if (!user) {
      return;
    }

    if (user.is_active) {
      setDeactivateCandidate(user);
      return;
    }

    setActionUserId(user.id);
    setError(null);

    try {
      const endpoint = user.is_active
        ? `/admin/users/${user.id}/deactivate`
        : `/admin/users/${user.id}/activate`;
      const updated = await request(endpoint, { method: "PATCH" });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (requestError) {
      setError({
        detail: requestError?.detail || "Не удалось обновить пользователя",
        code: requestError?.code || "UNKNOWN",
        errors: requestError?.errors || null,
      });
    } finally {
      setActionUserId(null);
    }
  };

  const confirmDeactivate = async () => {
    if (!deactivateCandidate) {
      return;
    }

    setActionUserId(deactivateCandidate.id);
    setError(null);

    try {
      const updated = await request(`/admin/users/${deactivateCandidate.id}/deactivate`, {
        method: "PATCH",
      });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setDeactivateCandidate(null);
    } catch (requestError) {
      setError({
        detail: requestError?.detail || "Не удалось обновить пользователя",
        code: requestError?.code || "UNKNOWN",
        errors: requestError?.errors || null,
      });
    } finally {
      setActionUserId(null);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Admin Users</h2>
          <p className="muted">{usersCountLabel}</p>
        </div>
      </div>

      <ErrorBanner error={error} />

      <div className="admin-filters">
        <div className="form-block">
          <label htmlFor="admin-users-query">Search</label>
          <input
            id="admin-users-query"
            type="search"
            placeholder="email"
            value={queryInput}
            onChange={(event) => setQueryInput(event.target.value)}
          />
        </div>
        <div className="form-block">
          <label htmlFor="admin-users-status">Status</label>
          <select
            id="admin-users-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Active</th>
              <th>Admin</th>
              <th>Online</th>
              <th>Last seen</th>
              <th>Last login</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8}>
                  <div className="admin-skeleton" />
                </td>
              </tr>
            )}

            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={8} className="admin-empty">
                  Пользователи не найдены.
                </td>
              </tr>
            )}

            {!loading &&
              users.map((user) => {
                const isActionLoading = actionUserId === user.id;
                return (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>{user.is_active ? "Yes" : "No"}</td>
                    <td>{user.is_admin ? "Yes" : "No"}</td>
                    <td>
                      <span className={`online-badge ${user.online ? "online" : "offline"}`}>
                        {user.online ? "online" : "offline"}
                      </span>
                    </td>
                    <td>{formatDateTime(user.last_seen_at)}</td>
                    <td>{formatDateTime(user.last_login_at)}</td>
                    <td>{formatDateTime(user.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="ghost-button admin-action-button"
                        onClick={() => toggleActive(user)}
                        disabled={isActionLoading}
                      >
                        {isActionLoading
                          ? "Saving..."
                          : user.is_active
                            ? "Deactivate"
                            : "Activate"}
                      </button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {deactivateCandidate && (
        <div className="modal-backdrop" role="presentation" onClick={() => setDeactivateCandidate(null)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Подтвердите деактивацию</h2>
                <p className="muted">
                  Пользователь <strong>{deactivateCandidate.email}</strong> потеряет доступ к системе.
                </p>
              </div>
              <button
                type="button"
                className="ghost-button"
                onClick={() => setDeactivateCandidate(null)}
              >
                Закрыть
              </button>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="danger-button"
                onClick={confirmDeactivate}
                disabled={actionUserId === deactivateCandidate.id}
              >
                {actionUserId === deactivateCandidate.id ? "Сохраняем..." : "Deactivate"}
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={() => setDeactivateCandidate(null)}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default AdminUsers;
