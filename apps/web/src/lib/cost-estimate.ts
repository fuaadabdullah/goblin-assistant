export interface TextCostEstimate {
  estimated_tokens: number;
  estimated_cost_usd: number;
}

// Conservative default for "quick estimate" in the UI.
// Interpreted as USD per 1k tokens.
const DEFAULT_USD_PER_1K_TOKENS = 0.02;

const isEmojiCodePoint = (code: number): boolean =>
  (code >= 0x1f300 && code <= 0x1f9ff) ||
  (code >= 0x2600 && code <= 0x27bf) ||
  (code >= 0x1f600 && code <= 0x1f64f);

const countTextCharacterTypes = (text: string) => {
  let charCount = 0;
  let emojiCount = 0;
  let unicodeCount = 0;

  for (const char of text) {
    const code = char.charCodeAt(0);

    if (isEmojiCodePoint(code)) {
      emojiCount++;
    } else if (code > 127) {
      unicodeCount++;
    } else {
      charCount++;
    }
  }

  return { charCount, emojiCount, unicodeCount };
};

const estimateTokenCount = ({
  charCount,
  emojiCount,
  unicodeCount,
}: {
  charCount: number;
  emojiCount: number;
  unicodeCount: number;
}): number =>
  Math.max(8, Math.round(charCount / 4 + unicodeCount / 2 + emojiCount * 2));

const normalizeNumber = (value: number): number =>
  !isNaN(value) && isFinite(value) ? value : 0;

export function estimateFromText(text: string): TextCostEstimate {
  const cleaned = (text || '').trim();
  if (!cleaned) {
    return { estimated_tokens: 0, estimated_cost_usd: 0 };
  }

  const estimatedTokens = estimateTokenCount(countTextCharacterTypes(cleaned));
  const estimatedCostUsd = (estimatedTokens / 1000) * DEFAULT_USD_PER_1K_TOKENS;

  return {
    estimated_tokens: normalizeNumber(estimatedTokens),
    estimated_cost_usd: Number(normalizeNumber(estimatedCostUsd).toFixed(6)),
  };
}
