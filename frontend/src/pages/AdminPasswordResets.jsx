import { useEffect, useMemo, useState } from "react";

import { request } from "../api.js";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { formatDateTime } from "../date.js";

const STATUS_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Requested", value: "requested" },
  { label: "Processed", value: "processed" },
];

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const buildResetsPath = (status) => {
  if (status === "all") {
    return "/admin/password-resets";
  }
  return `/admin/password-resets?status=${status}`;
};

const mapIssueError = (error) => {
  if (error?.code === "RESET_ALREADY_PROCESSED") {
    return toError("Заявка уже обработана", error.code, error.errors || null);
  }
  return toError(
    error?.detail || "Не удалось выдать временный пароль",
    error?.code || "UNKNOWN",
    error?.errors || null
  );
};

const AdminPasswordResets = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("all");
  const [issuingRequestId, setIssuingRequestId] = useState(null);
  const [revealedSecret, setRevealedSecret] = useState(null);
  const [copyState, setCopyState] = useState("idle");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await request(buildResetsPath(status));
        if (!cancelled) {
          setItems(Array.isArray(data) ? data : []);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError({
            detail: requestError?.detail || "Не удалось загрузить очередь заявок",
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
  }, [status]);

  const countLabel = useMemo(() => {
    if (loading) {
      return "Загрузка...";
    }
    return `Заявок: ${items.length}`;
  }, [items.length, loading]);

  const issueTempPassword = async (item) => {
    setError(null);
    setIssuingRequestId(item.id);
    setCopyState("idle");

    try {
      const response = await request(`/admin/password-resets/${item.id}/issue-temp-password`, {
        method: "POST",
      });

      setRevealedSecret({
        requestId: item.id,
        email: item.email,
        tempPassword: response.temp_password,
        expiresAt: response.expires_at,
      });

      setItems((current) =>
        current.map((entry) =>
          entry.id === item.id
            ? {
                ...entry,
                status: "processed",
                processed_at: new Date().toISOString(),
              }
            : entry
        )
      );
    } catch (requestError) {
      setError(mapIssueError(requestError));
    } finally {
      setIssuingRequestId(null);
    }
  };

  const closeSecretModal = () => {
    setRevealedSecret(null);
    setCopyState("idle");
  };

  const copyTempPassword = async () => {
    if (!revealedSecret?.tempPassword) {
      return;
    }
    try {
      await navigator.clipboard.writeText(revealedSecret.tempPassword);
      setCopyState("copied");
    } catch (errorValue) {
      setCopyState("failed");
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Admin Password Resets</h2>
          <p className="muted">{countLabel}</p>
        </div>
      </div>

      <ErrorBanner error={error} />

      <div className="admin-filters">
        <div className="form-block">
          <label htmlFor="admin-resets-status">Status</label>
          <select
            id="admin-resets-status"
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
              <th>Requested at</th>
              <th>Status</th>
              <th>Processed at</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5}>
                  <div className="admin-skeleton" />
                </td>
              </tr>
            )}

            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={5} className="admin-empty">
                  Заявки не найдены.
                </td>
              </tr>
            )}

            {!loading &&
              items.map((item) => {
                const isRequested = item.status === "requested";
                const isIssuing = issuingRequestId === item.id;
                return (
                  <tr key={item.id}>
                    <td>{item.email}</td>
                    <td>{formatDateTime(item.requested_at)}</td>
                    <td>{item.status}</td>
                    <td>{formatDateTime(item.processed_at)}</td>
                    <td>
                      {isRequested ? (
                        <button
                          type="button"
                          className="primary-button admin-action-button"
                          onClick={() => issueTempPassword(item)}
                          disabled={isIssuing}
                        >
                          {isIssuing ? "Issuing..." : "Issue temp password"}
                        </button>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {revealedSecret && (
        <div className="modal-backdrop" role="presentation" onClick={closeSecretModal}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Temporary password</h2>
                <p className="muted">Email: {revealedSecret.email}</p>
              </div>
              <button type="button" className="ghost-button" onClick={closeSecretModal}>
                Закрыть
              </button>
            </div>

            <div className="modal-body">
              <div className="alert info">
                Пароль показывается один раз. Сохраните его безопасно перед закрытием.
              </div>
              <div className="admin-secret-box">
                <code>{revealedSecret.tempPassword}</code>
              </div>
              <p className="muted">Действует до: {formatDateTime(revealedSecret.expiresAt)}</p>
              <div className="modal-actions">
                <button type="button" className="primary-button" onClick={copyTempPassword}>
                  Copy
                </button>
              </div>
              {copyState === "copied" && <div className="alert success">Скопировано в буфер.</div>}
              {copyState === "failed" && (
                <ErrorBanner error={toError("Не удалось скопировать в буфер", "COPY_FAILED")} />
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default AdminPasswordResets;
