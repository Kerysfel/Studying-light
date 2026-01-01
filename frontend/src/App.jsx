import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { navItems } from "./navigation.js";

const getPageTitle = (pathname) => {
  const match = navItems.find((item) => item.to === pathname);
  return match ? match.label : "Studying Light";
};

const AppLayout = () => {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SL</div>
          <div className="brand-text">
            <div className="brand-title">Studying Light</div>
            <div className="brand-subtitle">Помощник для чтения и повторений</div>
          </div>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `nav-item${isActive ? " active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="status-pill">Локальный режим</div>
          <div className="status-meta">API: /api/v1</div>
        </div>
      </aside>
      <div className="content">
        <header className="topbar">
          <div>
            <div className="eyebrow">Рабочее пространство</div>
            <h1>{pageTitle}</h1>
          </div>
          <div className="topbar-actions">
            <Link className="ghost-button" to="/session">
              Начать сессию
            </Link>
            <Link className="primary-button" to="/import">
              Импорт JSON
            </Link>
          </div>
        </header>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
