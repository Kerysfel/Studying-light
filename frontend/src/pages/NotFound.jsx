import { Link } from "react-router-dom";

const NotFound = () => {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Страница не найдена</h2>
          <p className="muted">Такой страницы не существует.</p>
        </div>
      </div>
      <Link className="primary-button" to="/app">
        Вернуться в приложение
      </Link>
    </section>
  );
};

export default NotFound;
