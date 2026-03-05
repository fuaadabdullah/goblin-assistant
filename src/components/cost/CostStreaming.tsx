interface Props {
  streaming: boolean;
  streamLines: string[];
}

export const CostStreaming = ({ streaming, streamLines }: Props) => {
  if (!streaming && streamLines.length === 0) return null;

  return (
    <div className="streaming-panel">
      <div className="streaming-title">Live Estimation</div>
      <div className="streaming-body">
        {streamLines.map((line, index) => (
          <div key={`${line}-${index}`} className="streaming-line">
            {line}
          </div>
        ))}
        {streaming && <div className="streaming-line">Estimating...</div>}
      </div>
    </div>
  );
};
