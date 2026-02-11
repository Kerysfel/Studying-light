import { useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      setLoading(true);
      const response = await request("/auth/request-password-reset", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      if (response?.status === "ok") {
        setMessage("Если email существует, заявка на сброс пароля отправлена.");
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <h1>Сброс пароля</h1>
        <p className="muted">Введите email. Система всегда возвращает единый ответ.</p>

        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="form-block full">
            <label htmlFor="forgot-email">Email</label>
            <input
              id="forgot-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          {error && <div className="alert error full">{error}</div>}
          {message && <div className="alert success full">{message}</div>}

          <div className="auth-actions full">
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Отправляем..." : "Отправить"}
            </button>
            <Link className="ghost-button" to="/login">
              Назад ко входу
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
};

export default ForgotPassword;
