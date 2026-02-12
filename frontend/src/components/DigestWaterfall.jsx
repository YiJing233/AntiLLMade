export default function DigestWaterfall({ categories, onMarkRead }) {
  const cards = categories.flatMap(([category, items]) =>
    items.map((item) => ({ ...item, category }))
  );

  return (
    <div className="waterfall">
      {cards.map((item) => (
        <article key={item.id || item.link} className="waterfall-card">
          <p className="category-tag">{item.category}</p>
          <header>
            <h3>{item.title}</h3>
            <p>
              {item.source_title} · {new Date(item.published_at).toLocaleString()}
            </p>
          </header>
          <p className="summary">{item.summary}</p>
          <details>
            <summary>查看原文节选</summary>
            <p>{item.content || '无详细内容'}</p>
          </details>
          <div className="entry-actions">
            <a href={item.link} target="_blank" rel="noreferrer">
              阅读原文
            </a>
            {item.unread && (
              <button type="button" className="ghost" onClick={() => onMarkRead(item.id)}>
                标记已读
              </button>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
