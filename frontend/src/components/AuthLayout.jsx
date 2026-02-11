import { Link } from "react-router-dom";

const AuthLayout = ({ title, subtitle, children, footer = null }) => {
  return (
    <div className="auth-shell">
      <section className="panel auth-panel">
        <div className="auth-header">
          <div>
            <h1>{title}</h1>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <Link className="auth-back-link" to="/">
            Назад на landing
          </Link>
        </div>
        {children}
        {footer}
      </section>
    </div>
  );
};

export default AuthLayout;
