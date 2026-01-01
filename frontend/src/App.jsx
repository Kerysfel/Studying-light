import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { getErrorMessage, request } from "./api.js";
import { navItems } from "./navigation.js";

const getPageTitle = (pathname) => {
  const match = navItems.find((item) => item.to === pathname);
  return match ? match.label : "Studying Light";
};

const AppLayout = () => {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importPartId, setImportPartId] = useState("");
  const [importPayload, setImportPayload] = useState("");
  const [importError, setImportError] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  useEffect(() => {
    if (!showImportModal) {
      return;
    }
    const stored = localStorage.getItem("lastPartId");
    if (stored) {
      setImportPartId(stored);
    }
  }, [showImportModal]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timer = setTimeout(() => setToastMessage(""), 2400);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const openImportModal = () => {
    setImportError("");
    setShowImportModal(true);
  };

  const closeImportModal = () => {
    setImportError("");
    setShowImportModal(false);
  };

  const handleImport = async () => {
    setImportError("");
    if (!importPartId) {
      setImportError("Укажите ID части для импорта.");
      return;
    }
    if (!importPayload.trim()) {
      setImportError("Вставьте JSON для импорта.");
      return;
    }
    let data;
    try {
      data = JSON.parse(importPayload);
    } catch (err) {
      setImportError("Некорректный JSON. Проверь формат и попробуй снова.");
      return;
    }

    try {
      setImportLoading(true);
      const response = await request(`/parts/${importPartId}/import_gpt`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      const count = response.review_items?.length || 0;
      setToastMessage(`Импорт выполнен. Создано повторений: ${count}.`);
      setImportPayload("");
      setShowImportModal(false);
      window.dispatchEvent(new Event("dashboard:refresh"));
    } catch (err) {
      setImportError(getErrorMessage(err));
    } finally {
      setImportLoading(false);
    }
  };

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
            <NavLink className="ghost-button" to="/session">
              Начать сессию
            </NavLink>
            <button className="primary-button" type="button" onClick={openImportModal}>
              Импорт JSON
            </button>
          </div>
        </header>
        <main className="page">
          <Outlet />
        </main>
      </div>

      {showImportModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div>
                <h2>Импорт JSON</h2>
                <p className="muted">Вставьте ответ из ChatGPT.</p>
              </div>
              <button className="ghost-button" type="button" onClick={closeImportModal}>
                Закрыть
              </button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-block">
                  <label>ID части</label>
                  <input
                    value={importPartId}
                    onChange={(event) => setImportPartId(event.target.value)}
                    placeholder="Например, 12"
                  />
                </div>
                <div className="form-block full">
                  <label>JSON</label>
                  <textarea
                    rows="8"
                    value={importPayload}
                    onChange={(event) => setImportPayload(event.target.value)}
                    placeholder='{"gpt_summary": "...", "gpt_questions_by_interval": {...}}'
                  />
                </div>
              </div>
              {importError && <div className="alert error">{importError}</div>}
              <div className="modal-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={handleImport}
                  disabled={importLoading}
                >
                  {importLoading ? "Импорт..." : "Импортировать"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {toastMessage && <div className="toast">{toastMessage}</div>}
    </div>
  );
};

export default AppLayout;
