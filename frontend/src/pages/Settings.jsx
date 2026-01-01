const Settings = () => {
  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
          <h2>Параметры сессий</h2>
          <p className="muted">Настройте дневной ритм.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block">
            <label>Цель по будням (мин)</label>
            <input type="number" placeholder="40" />
          </div>
          <div className="form-block">
            <label>Цель на выходных (мин)</label>
            <input type="number" placeholder="60" />
          </div>
          <div className="form-block">
            <label>Помодоро: работа</label>
            <input type="number" placeholder="25" />
          </div>
          <div className="form-block">
            <label>Помодоро: перерыв</label>
            <input type="number" placeholder="5" />
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Интервалы</h2>
            <p className="muted">Частота повторений в днях.</p>
          </div>
        </div>
        <div className="pill-row">
          {["1", "7", "16", "35", "90"].map((value) => (
            <span key={value} className="pill">
              {value} д
            </span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Settings;
