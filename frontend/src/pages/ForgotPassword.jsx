import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { request } from "../api.js";
import AuthLayout from "../components/AuthLayout.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const clientValidationError = useMemo(() => {
    if (!email.trim()) {
      return toError("Введите email", "VALIDATION_ERROR");
    }
    return null;
  }, [email]);

  const canSubmit = !loading && !clientValidationError;

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (clientValidationError) {
      setError(clientValidationError);
      return;
    }

    setError(null);

    try {
      setLoading(true);
      await request("/auth/request-password-reset", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSuccess(true);
    } catch (requestError) {
      setError({
        detail: requestError?.detail || "Не удалось отправить заявку",
        code: requestError?.code || "UNKNOWN",
        errors: requestError?.errors || null,
      });
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <AuthLayout
        title="Заявка отправлена"
        subtitle="Если аккаунт существует, заявка создана. Администратор выдаст временный пароль."
      >
        <div className="auth-actions">
          <Link className="primary-button" to="/login" state={{ email }}>
            К входу
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Сброс пароля" subtitle="Введите email для создания заявки на временный пароль.">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-block full">
          <label htmlFor="forgot-email">Email</label>
          <input
            id="forgot-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoFocus
            required
          />
        </div>

        {clientValidationError && !error && <ErrorBanner error={clientValidationError} />}
        <ErrorBanner error={error} />

        <div className="auth-actions full">
          <button className="primary-button" type="submit" disabled={!canSubmit}>
            {loading ? "Отправляем..." : "Отправить"}
          </button>
          <Link className="ghost-button" to="/login">
            Назад ко входу
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};

export default ForgotPassword;
