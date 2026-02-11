import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { getErrorMessage, request } from "../api.js";
import { useAuth } from "../auth.jsx";

const ForceChangePassword = () => {
  const navigate = useNavigate();
  const { refreshMe, logout } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      setLoading(true);
      await request("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      await refreshMe();
      setMessage("Пароль обновлен.");
      navigate("/app", { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <h1>Смените пароль</h1>
        <p className="muted">Для продолжения работы обновите пароль.</p>

        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="form-block full">
            <label htmlFor="force-current">Текущий пароль</label>
            <input
              id="force-current"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
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

          {error && <div className="alert error full">{error}</div>}
          {message && <div className="alert success full">{message}</div>}

          <div className="auth-actions full">
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Сохраняем..." : "Сменить пароль"}
            </button>
            <button className="ghost-button" type="button" onClick={logout}>
              Выйти
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};

export default ForceChangePassword;
