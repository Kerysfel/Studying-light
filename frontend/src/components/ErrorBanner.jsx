const normalizeErrorsList = (error) => {
  if (!error) {
    return [];
  }

  if (Array.isArray(error.errors)) {
    return error.errors.map((item) => {
      if (typeof item === "string") {
        return item;
      }
      if (item && typeof item === "object") {
        if (item.msg && item.loc) {
          const location = Array.isArray(item.loc) ? item.loc.join(".") : String(item.loc);
          return `${location}: ${item.msg}`;
        }
        if (item.msg) {
          return item.msg;
        }
      }
      return String(item);
    });
  }

  return [];
};

const ErrorBanner = ({ error }) => {
  if (!error) {
    return null;
  }

  const detail = error.detail || "Произошла ошибка";
  const code = error.code || "UNKNOWN";
  const detailsList = normalizeErrorsList(error);

  return (
    <div className="alert error error-banner" role="alert">
      <div className="error-banner-header">
        <span>{detail}</span>
        <small>({code})</small>
      </div>
      {detailsList.length > 0 && (
        <ul className="error-banner-list">
          {detailsList.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ErrorBanner;
