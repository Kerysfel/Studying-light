import { Link } from "react-router-dom";

const Landing = () => {
  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <p className="eyebrow">Studying Light</p>
        <h1>Учитесь быстрее, повторяйте регулярно</h1>
        <p className="muted">
          Войдите в аккаунт, чтобы продолжить работу с книгами, повторениями и алгоритмами.
        </p>
        <div className="auth-actions">
          <Link className="primary-button" to="/login">
            Войти
          </Link>
          <Link className="ghost-button" to="/register">
            Регистрация
          </Link>
        </div>
      </section>
    </div>
  );
};

export default Landing;
