import DigestWaterfall from '../components/DigestWaterfall.jsx';

export default function Digest({
  date,
  setDate,
  digest,
  categories,
  loading,
  error,
  onRefreshDigest,
  onIngestNow,
  onMarkRead
}) {
  return (
    <>
      <header className="header">
        <div>
          <p className="eyebrow">AI 理解驱动的 RSS 日报</p>
          <h1>长上下文资讯阅读站</h1>
          <p className="subtitle">按日期与主题聚合，先摘要、后细节、再原文链接，帮助快速阅读。</p>
        </div>
        <div className="actions">
          <label>
            日报日期
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <button onClick={onRefreshDigest} disabled={loading}>
            刷新日报
          </button>
          <button onClick={onIngestNow} disabled={loading}>
            立即拉取
          </button>
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <h2>{digest ? `${digest.date} 汇总日报` : '每日汇总日报'}</h2>
          {digest && <span>{digest.total} 条更新</span>}
        </div>
        {loading && <p>正在加载...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && categories.length === 0 && <p>暂无日报内容。</p>}
        {!loading && !error && categories.length > 0 && (
          <DigestWaterfall categories={categories} onMarkRead={onMarkRead} />
        )}
      </section>
    </>
  );
}
