const AdminPagination = ({
  total,
  limit,
  offset,
  onChange,
}) => {
  const safeTotal = Math.max(0, Number(total || 0));
  const safeLimit = Math.max(1, Number(limit || 1));
  const safeOffset = Math.max(0, Number(offset || 0));

  const pageStart = safeTotal === 0 ? 0 : safeOffset + 1;
  const pageEnd = Math.min(safeTotal, safeOffset + safeLimit);
  const canGoPrev = safeOffset > 0;
  const canGoNext = safeOffset + safeLimit < safeTotal;

  return (
    <div className="admin-pagination">
      <div className="muted">
        Показано: {pageStart}-{pageEnd} из {safeTotal}
      </div>
      <div className="admin-pagination-actions">
        <button
          type="button"
          className="ghost-button"
          onClick={() => onChange(Math.max(0, safeOffset - safeLimit))}
          disabled={!canGoPrev}
        >
          Назад
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={() => onChange(safeOffset + safeLimit)}
          disabled={!canGoNext}
        >
          Вперед
        </button>
      </div>
    </div>
  );
};

export default AdminPagination;
