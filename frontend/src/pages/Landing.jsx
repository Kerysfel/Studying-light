import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

const howItWorks = [
  "Создаёшь книгу, читаешь часть и фиксируешь сессию с помодоро.",
  "Генерируешь промпт и импортируешь JSON с вопросами и сводкой.",
  "Повторяешь по расписанию отдельно теорию и алгоритмы.",
  "Проверяешь ответы через GPT и отслеживаешь прогресс.",
];

const features = [
  "Книги и части с прогрессом чтения.",
  "Интервальные повторения с настраиваемыми интервалами (по умолчанию 1/7/16/35/90).",
  "Markdown-сводки и конспекты по частям.",
  "Отдельный словарь алгоритмов и алгоритмические повторения.",
  "Тренировки алгоритмов в режимах typing и memory.",
  "Админ-панель для активации пользователей и обработки reset-заявок.",
  "Экспорт данных в CSV и ZIP.",
];

const screenshots = [
  {
    src: "/landing/landing_dashboard.png",
    title: "Dashboard / Today",
    description: "Обзор активных книг и задач на сегодня.",
  },
  {
    src: "/landing/landing_session.png",
    title: "Reading Session",
    description: "Сессия чтения, заметки и таймер.",
  },
  {
    src: "/landing/landing_reviews.png",
    title: "Reviews",
    description: "Список повторений по теории и алгоритмам.",
  },
  {
    src: "/landing/landing_review_detail.png",
    title: "Review Detail",
    description: "Детали повторения с markdown summary.",
  },
  {
    src: "/landing/landing_import.png",
    title: "Import JSON",
    description: "Импорт результата GPT в часть книги.",
  },
];

const appVersion = import.meta.env.VITE_APP_VERSION || "dev";

const Landing = () => {
  const [activeShot, setActiveShot] = useState(null);

  const openScreenshot = (screenshot) => setActiveShot(screenshot);
  const closeScreenshot = () => setActiveShot(null);

  const featureItems = useMemo(
    () => features.map((feature) => <li key={feature}>{feature}</li>),
    []
  );

  return (
    <div className="landing-shell">
      <section className="panel landing-hero">
        <p className="eyebrow">Studying Light</p>
        <h1>Помощник для чтения, интервальных повторений и тренировок алгоритмов.</h1>
        <p className="muted landing-lead">
          Ведите книги по частям, превращайте конспекты в расписание повторений и отдельно
          прокачивайте алгоритмы в тренировочных режимах.
        </p>
        <div className="auth-actions">
          <Link className="primary-button" to="/register">
            Начать
          </Link>
          <Link className="ghost-button" to="/login">
            Войти
          </Link>
          <Link className="ghost-button" to="/app">
            Открыть приложение
          </Link>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Как работает</h2>
            <p className="muted">Поток работы в четыре шага.</p>
          </div>
        </div>
        <ol className="landing-steps">
          {howItWorks.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Возможности</h2>
            <p className="muted">Что уже доступно в приложении.</p>
          </div>
        </div>
        <ul className="landing-features">{featureItems}</ul>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Скриншоты</h2>
            <p className="muted">Интерфейс Dashboard, Session, Reviews и Import.</p>
          </div>
        </div>
        <div className="landing-gallery">
          {screenshots.map((shot) => (
            <button
              key={shot.src}
              type="button"
              className="landing-shot"
              onClick={() => openScreenshot(shot)}
            >
              <img src={shot.src} alt={shot.title} loading="lazy" />
              <div className="landing-shot-caption">
                <strong>{shot.title}</strong>
                <span>{shot.description}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <footer className="panel landing-footer">
        <a href="https://github.com/Kerysfel/Studying-light" target="_blank" rel="noreferrer">
          GitHub
        </a>
        <a href="docs/specs/pages.md" target="_blank" rel="noreferrer">
          Docs: docs/specs/pages.md
        </a>
        <span>Version: {appVersion}</span>
      </footer>

      {activeShot && (
        <div className="modal-backdrop" onClick={closeScreenshot} role="presentation">
          <div className="modal landing-lightbox" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{activeShot.title}</h2>
                <p className="muted">{activeShot.description}</p>
              </div>
              <button className="ghost-button" type="button" onClick={closeScreenshot}>
                Закрыть
              </button>
            </div>
            <img src={activeShot.src} alt={activeShot.title} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Landing;
