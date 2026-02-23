import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { request } from "../api.js";
import { useAuth } from "../auth.jsx";
import AuthLayout from "../components/AuthLayout.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const validateForm = ({ currentPassword, newPassword, confirmNewPassword }) => {
  if (!currentPassword || !newPassword || !confirmNewPassword) {
    return toError("Заполните все поля", "VALIDATION_ERROR");
  }
  if (!newPassword.trim() || !confirmNewPassword.trim()) {
    return toError("Новый пароль не может состоять только из пробелов", "VALIDATION_ERROR");
  }
  if (newPassword.length < 10) {
    return toError("Новый пароль должен быть не короче 10 символов", "VALIDATION_ERROR");
  }
  if (newPassword !== confirmNewPassword) {
    return toError("Новый пароль и подтверждение не совпадают", "VALIDATION_ERROR");
  }
  return null;
};

const ForceChangePassword = () => {
  const navigate = useNavigate();
  const { refreshMe, logout } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const clientValidationError = useMemo(
    () => validateForm({ currentPassword, newPassword, confirmNewPassword }),
    [confirmNewPassword, currentPassword, newPassword]
  );

  const canSubmit = !loading && !clientValidationError;

  const handleSubmit = async (event) => {
    event.preventDefault();

    const validationError = validateForm({ currentPassword, newPassword, confirmNewPassword });
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    try {
      setLoading(true);
      await request("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");

      await refreshMe();
      navigate("/app", { replace: true });
    } catch (requestError) {
      setError({
        detail: requestError?.detail || "Не удалось сменить пароль",
        code: requestError?.code || "UNKNOWN",
        errors: requestError?.errors || null,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Смените пароль" subtitle="Для продолжения работы обновите пароль.">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-block full">
          <label htmlFor="force-current">Текущий пароль</label>
          <input
            id="force-current"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="form-block full">
          <label htmlFor="force-new">Новый пароль</label>
          <input
            id="force-new"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            minLength={10}
            required
          />
        </div>
        <div className="form-block full">
          <label htmlFor="force-confirm-new">Подтвердите новый пароль</label>
          <input
            id="force-confirm-new"
            type="password"
            autoComplete="new-password"
            value={confirmNewPassword}
            onChange={(event) => setConfirmNewPassword(event.target.value)}
            minLength={10}
            required
          />
        </div>

        {clientValidationError && !error && <ErrorBanner error={clientValidationError} />}
        <ErrorBanner error={error} />

        <div className="auth-actions full">
          <button className="primary-button" type="submit" disabled={!canSubmit}>
            {loading ? "Сохраняем..." : "Сменить пароль"}
          </button>
          <button className="ghost-button" type="button" onClick={logout}>
            Выйти
          </button>
        </div>
      </form>
    </AuthLayout>
  );
};

export default ForceChangePassword;
