export default function SourceCards({ sourceMeta, onRemove }) {
  return (
    <div className="source-grid">
      {sourceMeta.map((source) => (
        <article key={source.id}>
          <div className="source-header">
            <h3>{source.title}</h3>
            {source.has_unread && <span className="badge">未读 {source.unread_count}</span>}
          </div>
          <p>{source.category}</p>
          <a href={source.url} target="_blank" rel="noreferrer">
            {source.url}
          </a>
          <div className="source-meta">
            <span>
              最近更新: {source.latest_entry_at ? new Date(source.latest_entry_at).toLocaleString() : '暂无'}
            </span>
            <button className="ghost" type="button" onClick={() => onRemove(source.id)}>
              移除
            </button>
          </div>
        </article>
      ))}
      {sourceMeta.length === 0 && <p>暂无订阅源，请先添加。</p>}
    </div>
  );
}
