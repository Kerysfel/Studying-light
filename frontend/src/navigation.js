const baseNavItems = [
  { label: "Дашборд", to: "/app" },
  { label: "Сессия чтения", to: "/session" },
  { label: "Повторения", to: "/reviews" },
  { label: "Статистика", to: "/stats" },
  { label: "Книги", to: "/books" },
  { label: "Алгоритмы", to: "/algorithm-groups" },
  { label: "Настройки", to: "/settings" },
  { label: "Импорт/Экспорт", to: "/import" },
  { label: "О проекте", to: "/about" },
];

const adminNavItems = [
  { label: "Админ: пользователи", to: "/admin/users" },
  { label: "Админ: заявки", to: "/admin/password-resets" },
];

export const getNavItems = (isAdmin = false) => {
  if (!isAdmin) {
    return baseNavItems;
  }
  return [...baseNavItems, ...adminNavItems];
};
