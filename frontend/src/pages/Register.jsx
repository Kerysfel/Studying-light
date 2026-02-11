import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { request } from "../api.js";
import AuthLayout from "../components/AuthLayout.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const validateRegister = ({ email, password, confirmPassword }) => {
  if (!email.trim()) {
    return toError("Введите email", "VALIDATION_ERROR");
  }
  if (!password.trim() || !confirmPassword.trim()) {
    return toError("Пароль не может состоять только из пробелов", "VALIDATION_ERROR");
  }
  if (password.length < 10) {
    return toError("Пароль должен быть не короче 10 символов", "VALIDATION_ERROR");
  }
  if (password !== confirmPassword) {
    return toError("Пароли не совпадают", "VALIDATION_ERROR");
  }
  return null;
};

const Register = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isPendingActivation, setIsPendingActivation] = useState(false);

  const clientValidationError = useMemo(
    () => validateRegister({ email, password, confirmPassword }),
    [confirmPassword, email, password]
  );

  const canSubmit = !loading && !clientValidationError;

  const handleSubmit = async (event) => {
    event.preventDefault();
    const validationError = validateRegister({ email, password, confirmPassword });
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    try {
      setLoading(true);
      await request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, confirm_password: confirmPassword }),
      });
      setIsPendingActivation(true);
    } catch (requestError) {
      setError({
        detail: requestError?.detail || "Не удалось зарегистрироваться",
        code: requestError?.code || "UNKNOWN",
        errors: requestError?.errors || null,
      });
    } finally {
      setLoading(false);
    }
  };

  if (isPendingActivation) {
    return (
      <AuthLayout
        title="Регистрация успешна"
        subtitle="Ожидайте активации администратором. После активации можно войти в систему."
      >
        <div className="auth-actions">
          <Link className="primary-button" to="/login" state={{ email }}>
            Перейти ко входу
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Регистрация"
      subtitle="Создайте учетную запись. После регистрации нужна активация админом."
    >
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-block full">
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="form-block full">
          <label htmlFor="register-password">Пароль</label>
          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={10}
            required
          />
        </div>
        <div className="form-block full">
          <label htmlFor="register-confirm">Подтвердите пароль</label>
          <input
            id="register-confirm"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            minLength={10}
            required
          />
        </div>

        {clientValidationError && !error && <ErrorBanner error={clientValidationError} />}
        <ErrorBanner error={error} />

        <div className="auth-actions full">
          <button className="primary-button" type="submit" disabled={!canSubmit}>
            {loading ? "Создаем..." : "Зарегистрироваться"}
          </button>
        </div>
      </form>

      <p className="muted auth-note">
        Уже есть аккаунт? <Link className="inline-link" to="/login">Войти</Link>
      </p>
    </AuthLayout>
  );
};

export default Register;
