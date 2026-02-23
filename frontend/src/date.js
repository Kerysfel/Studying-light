const padValue = (value) => String(value).padStart(2, "0");

const buildDateKey = (value) => {
  if (!(value instanceof Date)) {
    return null;
  }
  return `${value.getFullYear()}-${padValue(value.getMonth() + 1)}-${padValue(
    value.getDate()
  )}`;
};

const parseDateValue = (value) => {
  if (!value) {
    return null;
  }
  if (value instanceof Date) {
    return value;
  }
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const [year, month, day] = text.split("-").map(Number);
    return new Date(year, month - 1, day);
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
};

export const formatDueDate = (value, { todayLabel = "Today" } = {}) => {
  if (!value) {
    return "-";
  }
  const parsed = parseDateValue(value);
  if (!parsed) {
    return String(value);
  }
  const valueKey = buildDateKey(parsed);
  const todayKey = buildDateKey(new Date());
  if (valueKey && todayKey && valueKey === todayKey) {
    return todayLabel;
  }
  const now = new Date();
  const includeYear = parsed.getFullYear() !== now.getFullYear();
  const formatter = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    ...(includeYear ? { year: "numeric" } : {}),
  });
  return formatter.format(parsed);
};

export const formatDateTime = (value) => {
  if (!value) {
    return "-";
  }
  const parsed = parseDateValue(value);
  if (!parsed) {
    return String(value);
  }
  const formatter = new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return formatter.format(parsed);
};
