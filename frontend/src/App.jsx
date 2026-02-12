import { useEffect, useMemo, useState } from 'react';
import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom';
import Sources from './pages/Sources.jsx';
import Digest from './pages/Digest.jsx';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const defaultSources = [
  { url: 'https://hnrss.org/frontpage', title: 'Hacker News', category: '科技' },
  {
    url: 'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
    title: 'NYTimes Tech',
    category: '全球'
  }
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
    try {
      const res = await fetch(`${API_BASE}/sources/meta`);
      const data = await res.json();
      setSourceMeta(data);
    } catch {
      setError('无法获取订阅源数据。');
    }
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
    try {
      await fetch(`${API_BASE}/sources/${sourceId}`, { method: 'DELETE' });
      await fetchSourceMeta();
    } catch {
      setError('无法移除订阅源。');
    }
  };

  const markRead = async (entryId) => {
    try {
      await fetch(`${API_BASE}/entries/${entryId}/read`, { method: 'POST' });
      await fetchDigest();
      await fetchSourceMeta();
    } catch {
      setError('标记已读失败。');
    }
  };

  const seedSources = async () => {
    try {
      for (const source of defaultSources) {
        await fetch(`${API_BASE}/sources`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(source)
        });
      }
      await fetchSourceMeta();
    } catch {
      setError('示例源填充失败。');
    }
  };

  useEffect(() => {
    fetchSourceMeta();
    fetchDigest();
  }, []);

  useEffect(() => {
    fetchDigest();
  }, [date]);

  return (
    <BrowserRouter>
      <div className="page">
        <nav className="top-nav">
          <NavLink to="/sources" className={({ isActive }) => (isActive ? 'active' : '')}>
            Sources
          </NavLink>
          <NavLink to="/digest" className={({ isActive }) => (isActive ? 'active' : '')}>
            Digest
          </NavLink>
        </nav>

        <Routes>
          <Route
            path="/sources"
            element={
              <Sources
                totalUnread={totalUnread}
                sourceMeta={sourceMeta}
                form={form}
                setForm={setForm}
                onCreateSource={createSource}
                onRemoveSource={removeSource}
                onRefreshSourceMeta={fetchSourceMeta}
                onSeedSources={seedSources}
                error={error}
              />
            }
          />
          <Route
            path="/digest"
            element={
              <Digest
                date={date}
                setDate={setDate}
                digest={digest}
                categories={categories}
                loading={loading}
                error={error}
                onRefreshDigest={fetchDigest}
                onIngestNow={ingestNow}
                onMarkRead={markRead}
              />
            }
          />
          <Route path="*" element={<Navigate to="/sources" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
