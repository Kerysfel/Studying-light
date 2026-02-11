export const mainNavItems = [
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

export const adminNavItems = [
  { label: "Users", to: "/admin/users" },
  { label: "Password resets", to: "/admin/password-resets" },
];

export const getNavSections = (isAdmin = false) => {
  const sections = [{ key: "main", title: null, items: mainNavItems }];
  if (isAdmin) {
    sections.push({ key: "admin", title: "Admin", items: adminNavItems });
  }
  return sections;
};
