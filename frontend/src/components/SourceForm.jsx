export default function SourceForm({ form, setForm, onSubmit }) {
  return (
    <form className="source-form" onSubmit={onSubmit}>
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
  );
}
