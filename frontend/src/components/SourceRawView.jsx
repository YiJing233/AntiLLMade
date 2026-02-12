export default function SourceRawView({ sourceMeta }) {
  return (
    <div className="raw-view">
      <pre>{JSON.stringify(sourceMeta, null, 2)}</pre>
    </div>
  );
}
