const API_BASE = "/api/v1";

const errorMessages = {
  INVALID_JSON_BODY: "Некорректный JSON. Проверь формат и попробуй снова.",
  VALIDATION_ERROR: "Проверьте введенные данные.",
  IMPORT_PAYLOAD_INVALID: "Некорректные данные импорта. Проверь формат.",
  NOT_FOUND: "Запрашиваемые данные не найдены.",
  BAD_REQUEST: "Запрос сформирован неправильно.",
  CONFLICT: "Конфликт данных. Обновите страницу и попробуйте снова.",
  UNAUTHORIZED: "Нужна авторизация.",
  FORBIDDEN: "Недостаточно прав для действия.",
  INTERNAL_ERROR: "Внутренняя ошибка сервера.",
  NETWORK_ERROR: "Ошибка сети. Проверьте подключение.",
};

const parseJson = async (response) => {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
};

const normalizeError = (status, payload) => {
  if (payload && typeof payload === "object") {
    return {
      detail: payload.detail || "Ошибка запроса",
      code: payload.code || `HTTP_${status}`,
      errors: payload.errors || null,
    };
  }
  return { detail: "Ошибка запроса", code: `HTTP_${status}`, errors: null };
};

export const request = async (path, options = {}) => {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    throw { detail: "Ошибка сети", code: "NETWORK_ERROR", errors: null };
  }
  const data = await parseJson(response);
  if (!response.ok) {
    throw normalizeError(response.status, data);
  }
  return data;
};

export const getErrorMessage = (error) => {
  if (!error) {
    return "Неизвестная ошибка.";
  }
  const code = error.code || null;
  if (code && errorMessages[code]) {
    return errorMessages[code];
  }
  if (error.detail) {
    return error.detail;
  }
  return "Неизвестная ошибка.";
};
