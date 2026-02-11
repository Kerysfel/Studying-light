import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { request } from "../api.js";
import { useAuth } from "../auth.jsx";
import AuthLayout from "../components/AuthLayout.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";

const toError = (detail, code, errors = null) => ({ detail, code, errors });

const mapLoginError = (error) => {
  const code = error?.code || "UNKNOWN";
  if (code === "ACCOUNT_INACTIVE") {
    return toError("Аккаунт не активирован администратором", code, error?.errors || null);
  }
  if (code === "AUTH_INVALID" || code === "HTTP_401") {
    return toError("Неверный email или пароль", code, error?.errors || null);
  }
  return toError(error?.detail || "Ошибка входа", code, error?.errors || null);
};

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { completeLogin, consumeLoginNotice, loginNotice } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stateEmail = location.state?.email;
    if (stateEmail) {
      setEmail(stateEmail);
    }
  }, [location.state]);

  useEffect(() => {
    if (!loginNotice) {
      return;
    }
    const notice = consumeLoginNotice();
    if (!notice) {
      return;
    }
    if (notice.email) {
      setEmail(notice.email);
    }
    setError(mapLoginError(notice));
  }, [consumeLoginNotice, loginNotice]);

  const canSubmit = useMemo(() => {
    return email.trim().length > 0 && password.length > 0 && !loading;
  }, [email, loading, password]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    setError(null);

    try {
      setLoading(true);
      const tokenResponse = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const me = await completeLogin(tokenResponse.access_token);
      const redirectTo = location.state?.from || "/app";
      if (me?.must_change_password) {
        navigate("/force-change-password", { replace: true });
        return;
      }
      navigate(redirectTo, { replace: true });
    } catch (requestError) {
      setError(mapLoginError(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Вход" subtitle="Введите email и пароль.">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-block full">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="form-block full">
          <label htmlFor="login-password">Пароль</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>

        <ErrorBanner error={error} />

        <div className="auth-actions full">
          <button className="primary-button" type="submit" disabled={!canSubmit}>
            {loading ? "Входим..." : "Войти"}
          </button>
          <Link className="ghost-button" to="/forgot-password">
            Забыли пароль?
          </Link>
        </div>
      </form>

      <p className="muted auth-note">
        Нет аккаунта? <Link className="inline-link" to="/register">Регистрация</Link>
      </p>
    </AuthLayout>
  );
};

export default Login;
