import { useState } from 'react';
import SourceForm from '../components/SourceForm.jsx';
import SourceCards from '../components/SourceCards.jsx';
import SourceRawView from '../components/SourceRawView.jsx';

export default function Sources({
  totalUnread,
  sourceMeta,
  form,
  setForm,
  onCreateSource,
  onRemoveSource,
  onRefreshSourceMeta,
  onSeedSources,
  error
}) {
  const [viewMode, setViewMode] = useState('crud');

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>订阅源管理</h2>
          <p className="panel-subtitle">未读汇总：{totalUnread} 条</p>
        </div>
        <div className="panel-actions">
          <button className={viewMode === 'crud' ? '' : 'ghost'} type="button" onClick={() => setViewMode('crud')}>
            CRUD 视图
          </button>
          <button className={viewMode === 'raw' ? '' : 'ghost'} type="button" onClick={() => setViewMode('raw')}>
            Raw 视图
          </button>
          <button className="ghost" type="button" onClick={onRefreshSourceMeta}>
            刷新订阅
          </button>
          <button type="button" onClick={onSeedSources}>
            一键填充示例源
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {viewMode === 'crud' ? (
        <>
          <SourceForm form={form} setForm={setForm} onSubmit={onCreateSource} />
          <SourceCards sourceMeta={sourceMeta} onRemove={onRemoveSource} />
        </>
      ) : (
        <SourceRawView sourceMeta={sourceMeta} />
      )}
    </section>
  );
}
