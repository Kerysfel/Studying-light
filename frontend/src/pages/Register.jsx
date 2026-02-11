import { useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const Register = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isPendingActivation, setIsPendingActivation] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    try {
      setLoading(true);
      await request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, confirm_password: confirmPassword }),
      });
      setIsPendingActivation(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  if (isPendingActivation) {
    return (
      <div className="auth-shell">
        <section className="panel auth-panel">
          <h1>Активация ожидается</h1>
          <p className="muted">
            Аккаунт создан. Дождитесь активации администратором, затем войдите в систему.
          </p>
          <div className="auth-actions">
            <Link className="primary-button" to="/login" state={{ email }}>
              К входу
            </Link>
            <Link className="ghost-button" to="/">
              На главную
            </Link>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <h1>Регистрация</h1>
        <p className="muted">Создайте учетную запись. После регистрации нужна активация админом.</p>

        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="form-block full">
            <label htmlFor="register-email">Email</label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
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
              required
              minLength={10}
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
              required
              minLength={10}
            />
          </div>

          {error && <div className="alert error full">{error}</div>}

          <div className="auth-actions full">
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Создаем..." : "Зарегистрироваться"}
            </button>
            <Link className="ghost-button" to="/login">
              Войти
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
};

export default Register;
