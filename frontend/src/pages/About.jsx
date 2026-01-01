const About = () => {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>О Studying Light</h2>
          <p className="muted">
            Минималистичный процесс чтения с интервальными повторениями.
          </p>
        </div>
      </div>
      <div className="about-grid">
        <div className="about-card">
          <div className="about-label">Цель</div>
          <div className="about-value">
            Делить чтение на компактные части с понятными циклами повторений.
          </div>
        </div>
        <div className="about-card">
          <div className="about-label">Стек</div>
          <div className="about-value">FastAPI, SQLite, React, Vite.</div>
        </div>
        <div className="about-card">
          <div className="about-label">Код</div>
          <div className="about-value">Открытый исходный код, проект сообщества.</div>
        </div>
      </div>
    </section>
  );
};

export default About;
