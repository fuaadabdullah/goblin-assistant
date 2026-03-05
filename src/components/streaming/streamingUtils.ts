export interface TokenChunk {
  text: string;
  isCode: boolean;
  index: number;
}

export const getNewChunk = (previousText: string, currentText: string): string => {
  if (!currentText.startsWith(previousText)) {
    return currentText;
  }
  return currentText.slice(previousText.length);
};

export const toTokenChunk = (chunk: string, fullText: string): TokenChunk => {
  const trimmed = chunk.trim();
  const isCode = trimmed.startsWith('```') || trimmed.startsWith('`');
  return {
    text: chunk,
    isCode,
    index: fullText.length,
  };
};
