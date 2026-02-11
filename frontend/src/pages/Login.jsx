import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";
import { useAuth } from "../auth.jsx";

const INACTIVE_MESSAGE =
  '{detail: "Account inactive, ask admin to activate", code: "ACCOUNT_INACTIVE"}';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { completeLogin, consumeLoginNotice, loginNotice } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [inactiveMessage, setInactiveMessage] = useState("");
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
    if (notice.code === "ACCOUNT_INACTIVE") {
      setInactiveMessage(INACTIVE_MESSAGE);
      return;
    }
    setError(getErrorMessage(notice));
  }, [consumeLoginNotice, loginNotice]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setInactiveMessage("");

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
      if (requestError?.code === "ACCOUNT_INACTIVE") {
        setInactiveMessage(INACTIVE_MESSAGE);
      } else {
        setError(getErrorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <h1>Вход</h1>
        <p className="muted">Введите email и пароль.</p>

        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="form-block full">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
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

          {inactiveMessage && <div className="alert info full">{inactiveMessage}</div>}
          {error && <div className="alert error full">{error}</div>}

          <div className="auth-actions full">
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Входим..." : "Войти"}
            </button>
            <Link className="ghost-button" to="/forgot-password">
              Забыли пароль?
            </Link>
            <Link className="ghost-button" to="/register">
              К регистрации
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
};

export default Login;
