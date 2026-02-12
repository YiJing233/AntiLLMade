import { useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const defaultSources = [
  { url: 'https://hnrss.org/frontpage', title: 'Hacker News', category: '科技' },
  { url: 'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml', title: 'NYTimes Tech', category: '全球' }
];

export default function App() {
  const [sourceMeta, setSourceMeta] = useState([]);
  const [digest, setDigest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState('');
  const [form, setForm] = useState({ url: '', title: '', category: '默认' });

  const categories = useMemo(() => {
    if (!digest) return [];
    return Object.entries(digest.categories || {});
  }, [digest]);

  const totalUnread = useMemo(() => {
    return sourceMeta.reduce((sum, source) => sum + (source.unread_count || 0), 0);
  }, [sourceMeta]);

  const fetchSourceMeta = async () => {
    const res = await fetch(`${API_BASE}/sources/meta`);
    const data = await res.json();
    setSourceMeta(data);
  };

  const fetchDigest = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/digest?date=${date}`);
      if (!res.ok) {
        throw new Error('无法获取日报。');
      }
      const data = await res.json();
      setDigest(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const ingestNow = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: 'POST' });
      if (!res.ok) {
        const message = await res.json();
        throw new Error(message.detail || '拉取失败');
      }
      await fetchDigest();
      await fetchSourceMeta();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createSource = async (event) => {
    event.preventDefault();
    setError('');
    try {
      const res = await fetch(`${API_BASE}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      if (!res.ok) {
        throw new Error('无法添加订阅源。');
      }
      setForm({ url: '', title: '', category: '默认' });
      await fetchSourceMeta();
    } catch (err) {
      setError(err.message);
    }
  };

  const removeSource = async (sourceId) => {
    setError('');
    await fetch(`${API_BASE}/sources/${sourceId}`, { method: 'DELETE' });
    await fetchSourceMeta();
  };

  const markRead = async (entryId) => {
    await fetch(`${API_BASE}/entries/${entryId}/read`, { method: 'POST' });
    await fetchDigest();
    await fetchSourceMeta();
  };

  const seedSources = async () => {
    for (const source of defaultSources) {
      await fetch(`${API_BASE}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(source)
      });
    }
    await fetchSourceMeta();
  };

  useEffect(() => {
    fetchSourceMeta();
    fetchDigest();
  }, []);

  useEffect(() => {
    fetchDigest();
  }, [date]);

  return (
    <div className="page">
      <header className="header">
        <div>
          <p className="eyebrow">AI 理解驱动的 RSS 日报</p>
          <h1>长上下文资讯阅读站</h1>
          <p className="subtitle">
            按日期与主题聚合，先摘要、后细节、再原文链接，帮助快速阅读。
          </p>
        </div>
        <div className="actions">
          <label>
            日报日期
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <button onClick={fetchDigest} disabled={loading}>刷新日报</button>
          <button onClick={ingestNow} disabled={loading}>立即拉取</button>
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>订阅源管理</h2>
            <p className="panel-subtitle">未读汇总：{totalUnread} 条</p>
          </div>
          <div className="panel-actions">
            <button className="ghost" type="button" onClick={fetchSourceMeta}>刷新订阅</button>
            <button onClick={seedSources}>一键填充示例源</button>
          </div>
        </div>
        <form className="source-form" onSubmit={createSource}>
          <input
            type="text"
            placeholder="订阅源名称"
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            required
          />
          <input
            type="url"
            placeholder="订阅源链接"
            value={form.url}
            onChange={(event) => setForm({ ...form, url: event.target.value })}
            required
          />
          <input
            type="text"
            placeholder="分类"
            value={form.category}
            onChange={(event) => setForm({ ...form, category: event.target.value })}
          />
          <button type="submit">添加订阅源</button>
        </form>
        <div className="source-grid">
          {sourceMeta.map((source) => (
            <article key={source.id}>
              <div className="source-header">
                <h3>{source.title}</h3>
                {source.has_unread && (
                  <span className="badge">未读 {source.unread_count}</span>
                )}
              </div>
              <p>{source.category}</p>
              <a href={source.url} target="_blank" rel="noreferrer">{source.url}</a>
              <div className="source-meta">
                <span>最近更新: {source.latest_entry_at ? new Date(source.latest_entry_at).toLocaleString() : '暂无'}</span>
                <button className="ghost" type="button" onClick={() => removeSource(source.id)}>移除</button>
              </div>
            </article>
          ))}
          {sourceMeta.length === 0 && <p>暂无订阅源，请先添加。</p>}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{digest ? `${digest.date} 汇总日报` : '每日汇总日报'}</h2>
          {digest && <span>{digest.total} 条更新</span>}
        </div>
        {loading && <p>正在加载...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && categories.length === 0 && <p>暂无日报内容。</p>}
        <div className="digest-grid">
          {categories.map(([category, items]) => (
            <div key={category} className="category">
              <h3>{category}</h3>
              {items.map((item) => (
                <article key={item.link}>
                  <header>
                    <h4>{item.title}</h4>
                    <p>{item.source_title} · {new Date(item.published_at).toLocaleString()}</p>
                  </header>
                  <p className="summary">{item.summary}</p>
                  <details>
                    <summary>查看原文节选</summary>
                    <p>{item.content || '无详细内容'}</p>
                  </details>
                  <div className="entry-actions">
                    <a href={item.link} target="_blank" rel="noreferrer">阅读原文</a>
                    {item.unread && (
                      <button type="button" className="ghost" onClick={() => markRead(item.id)}>
                        标记已读
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
