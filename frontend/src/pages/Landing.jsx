import { useState } from "react";
import { Link } from "react-router-dom";

const howItWorks = [
  {
    title: "Создайте книгу и начните сессию",
    description: "Добавьте книгу, откройте нужную часть и зафиксируйте чтение в формате помодоро.",
  },
  {
    title: "Импортируйте результат обработки",
    description: "Сгенерируйте промпт и загрузите JSON с вопросами и сводкой в выбранную часть.",
  },
  {
    title: "Запустите интервальные повторения",
    description: "Повторяйте теорию и алгоритмы по расписанию с заданными интервалами.",
  },
  {
    title: "Оценивайте ответы и прогресс",
    description: "Проверяйте ответы через GPT и отслеживайте динамику обучения на Dashboard.",
  },
];

const featureCards = [
  {
    tag: "Reading",
    title: "Чтение и прогресс",
    description:
      "Книги и части с фиксацией сессий, заметок и текущего прогресса в одном рабочем потоке.",
  },
  {
    tag: "Reviews",
    title: "Интервальные повторения",
    description:
      "Автоматическое расписание повторений по интервалам 1/7/16/35/90 и отдельные очереди по темам.",
  },
  {
    tag: "Algorithms",
    title: "Тренировки алгоритмов",
    description:
      "Отдельный словарь алгоритмов и тренировочные режимы typing и memory для закрепления решений.",
  },
  {
    tag: "Data",
    title: "Импорт/экспорт",
    description:
      "Импорт JSON из внешней обработки и выгрузка данных в CSV/ZIP для переноса и резервирования.",
  },
  {
    tag: "Admin",
    title: "Администрирование",
    description:
      "Управление пользователями, активацией аккаунтов и обработкой заявок на сброс пароля.",
  },
];

const screenshots = [
  {
    src: "landing/landing_dashboard.png",
    title: "Dashboard / Today",
    description: "Обзор активных книг и задач на сегодня.",
  },
  {
    src: "landing/landing_session.png",
    title: "Reading Session",
    description: "Сессия чтения, заметки и таймер.",
  },
  {
    src: "landing/landing_reviews.png",
    title: "Reviews",
    description: "Список повторений по теории и алгоритмам.",
  },
  {
    src: "landing/landing_review_detail.png",
    title: "Review Detail",
    description: "Детали повторения с markdown summary.",
  },
  {
    src: "landing/landing_import.png",
    title: "Import JSON",
    description: "Импорт результата GPT в часть книги.",
  },
  {
    src: "landing/landing_export.png",
    title: "Export CSV / ZIP",
    description: "Экспорт профиля и данных повторений в CSV/ZIP.",
  },
  {
    src: "landing/landing_auth_login.png",
    title: "Auth / Login",
    description: "Экран входа пользователя.",
  },
  {
    src: "landing/landing_auth_register.png",
    title: "Auth / Register",
    description: "Экран регистрации нового аккаунта.",
  },
  {
    src: "landing/landing_admin_users.png",
    title: "Admin / Users",
    description: "Администрирование пользователей и статусов аккаунтов.",
  },
];

const navItems = [
  { href: "#how-it-works", label: "Как работает" },
  { href: "#features", label: "Возможности" },
  { href: "#screenshots", label: "Скриншоты" },
  { href: "#faq-contacts", label: "FAQ / Контакты" },
];

const FALLBACK_IMAGE_SRC =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 800'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%23f6eee2'/%3E%3Cstop offset='100%25' stop-color='%23ece1d1'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1280' height='800' fill='url(%23g)'/%3E%3Ctext x='50%25' y='48%25' text-anchor='middle' fill='%23655a4f' font-family='Arial, sans-serif' font-size='46'%3EPreview unavailable%3C/text%3E%3Ctext x='50%25' y='56%25' text-anchor='middle' fill='%2381776d' font-family='Arial, sans-serif' font-size='26'%3EReload page or check static files%3C/text%3E%3C/svg%3E";

const appVersion = import.meta.env.VITE_APP_VERSION || "dev";
const appBaseUrl = import.meta.env.BASE_URL || "/";

const resolveAssetPath = (path) => {
  const normalizedBase = appBaseUrl.endsWith("/") ? appBaseUrl : `${appBaseUrl}/`;
  return `${normalizedBase}${path.replace(/^\/+/, "")}`;
};

const Landing = () => {
  const [activeShot, setActiveShot] = useState(null);

  const openScreenshot = (screenshot) => setActiveShot(screenshot);
  const closeScreenshot = () => setActiveShot(null);
  const handleImageLoadError = (event) => {
    const image = event.currentTarget;
    if (image.dataset.fallbackApplied === "true") {
      return;
    }
    image.dataset.fallbackApplied = "true";
    image.src = FALLBACK_IMAGE_SRC;
  };

  return (
    <div className="landing-shell">
      <header className="landing-header">
        <Link className="landing-brand" to="/">
          <span className="landing-brand-mark">SL</span>
          <span className="landing-brand-title">Studying Light</span>
        </Link>
        <nav className="landing-nav" aria-label="Навигация по лендингу">
          {navItems.map((item) => (
            <a key={item.href} className="landing-nav-link" href={item.href}>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="landing-auth">
          <Link className="ghost-button" to="/login">
            Войти
          </Link>
          <Link className="primary-button" to="/register">
            Регистрация
          </Link>
        </div>
      </header>

      <section className="panel landing-hero" id="top">
        <div className="landing-hero-layout">
          <div className="landing-hero-copy">
            <p className="eyebrow">Studying Light</p>
            <h1>
              Помощник для чтения, <span className="landing-accent-text">интервальных повторений</span>{" "}
              и тренировок алгоритмов.
            </h1>
            <p className="muted landing-lead">
              Ведите книги по частям, превращайте конспекты в расписание повторений и отдельно
              прокачивайте алгоритмы в тренировочных режимах.
            </p>
            <p className="muted landing-hero-note">
              Основной сценарий: регистрация, создание первой книги и старт первой сессии.
            </p>
            <div className="landing-hero-actions">
              <Link className="primary-button" to="/register">
                Начать
              </Link>
              <a className="ghost-button" href="#how-it-works">
                Подробнее
              </a>
            </div>
            <div className="landing-hero-pills" aria-hidden="true">
              <span>Помодоро-сессии</span>
              <span>Повторения 1/7/16/35/90</span>
              <span>Алгоритмы: typing + memory</span>
            </div>
          </div>
          <div className="landing-hero-visual">
            <div className="landing-hero-chip landing-hero-chip-top">
              <strong>Today</strong>
              <span>12 карточек в плане</span>
            </div>
            <div className="landing-hero-chip landing-hero-chip-bottom">
              <strong>Streak</strong>
              <span>9 дней подряд</span>
            </div>
            <div className="landing-hero-mockup">
              <img
                src={resolveAssetPath("landing/landing_dashboard.png")}
                alt="Интерфейс Dashboard приложения"
                onError={handleImageLoadError}
              />
            </div>
          </div>
        </div>
      </section>

      <section className="panel landing-section" id="how-it-works">
        <div className="panel-header">
          <div>
            <h2>Как работает</h2>
            <p className="muted">Поток работы в четыре шага.</p>
          </div>
        </div>
        <div className="landing-flow" role="list">
          {howItWorks.map((step, index) => (
            <article className="landing-flow-step" key={step.title} role="listitem">
              <span className="landing-flow-index">{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
              <p className="muted">{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel landing-section" id="features">
        <div className="panel-header">
          <div>
            <h2>Возможности</h2>
            <p className="muted">Функциональность сгруппирована по ключевым сценариям продукта.</p>
          </div>
        </div>
        <div className="landing-feature-grid" role="list">
          {featureCards.map((feature) => (
            <article className="landing-feature-card" key={feature.title} role="listitem">
              <span className="landing-feature-tag">{feature.tag}</span>
              <h3>{feature.title}</h3>
              <p className="muted">{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel landing-section" id="screenshots">
        <div className="panel-header">
          <div>
            <h2>Скриншоты</h2>
            <p className="muted">
              Ключевые экраны: Dashboard, Session, Reviews, Import/Export, Auth и Admin.
            </p>
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
              <img
                src={resolveAssetPath(shot.src)}
                alt={shot.title}
                loading="lazy"
                onError={handleImageLoadError}
              />
              <div className="landing-shot-caption">
                <strong>{shot.title}</strong>
                <span>{shot.description}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="panel landing-section" id="faq-contacts">
        <div className="panel-header">
          <div>
            <h2>FAQ / Контакты</h2>
            <p className="muted">Куда писать и где следить за обновлениями.</p>
          </div>
        </div>
        <ul className="landing-list landing-features">
          <li>
            <strong>Кому подходит?</strong> Тем, кто читает техническую литературу и хочет
            системно закреплять знания.
          </li>
          <li>
            <strong>Как начать?</strong> Зарегистрируйтесь, создайте книгу и импортируйте первую
            сводку.
          </li>
          <li>
            <strong>Контакты:</strong>{" "}
            <a
              className="landing-inline-link"
              href="https://github.com/Kerysfel/Studying-light"
              target="_blank"
              rel="noreferrer"
            >
              GitHub проекта
            </a>
          </li>
        </ul>
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
            <img
              src={resolveAssetPath(activeShot.src)}
              alt={activeShot.title}
              onError={handleImageLoadError}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default Landing;
