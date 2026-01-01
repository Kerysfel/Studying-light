import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const ImportExport = () => {
  const [partId, setPartId] = useState("");
  const [payload, setPayload] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("lastPartId");
    if (stored) {
      setPartId(stored);
    }
  }, []);

  const handleImport = async () => {
    setError("");
    setSuccess("");
    if (!partId) {
      setError("Укажите ID части для импорта.");
      return;
    }
    if (!payload.trim()) {
      setError("Вставьте JSON для импорта.");
      return;
    }

    let data;
    try {
      data = JSON.parse(payload);
    } catch (err) {
      setError("Некорректный JSON. Проверь формат и попробуй снова.");
      return;
    }

    try {
      setLoading(true);
      const response = await request(`/parts/${partId}/import_gpt`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      const count = response.review_items?.length || 0;
      setSuccess(`Импорт выполнен. Создано повторений: ${count}.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Импорт JSON</h2>
            <p className="muted">Вставьте ответ из ChatGPT.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block">
            <label>ID части</label>
            <input
              value={partId}
              onChange={(event) => setPartId(event.target.value)}
              placeholder="Например, 12"
            />
          </div>
          <div className="form-block full">
            <label>JSON</label>
            <textarea
              rows="8"
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              placeholder='{"gpt_summary": "...", "gpt_questions_by_interval": {...}}'
            />
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        <div className="form-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleImport}
            disabled={loading}
          >
            {loading ? "Импорт..." : "Импортировать"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Экспорт</h2>
            <p className="muted">Скачайте данные в формате JSON.</p>
          </div>
        </div>
        <button className="ghost-button" type="button">
          Экспортировать все
        </button>
      </section>
    </div>
  );
};

export default ImportExport;
