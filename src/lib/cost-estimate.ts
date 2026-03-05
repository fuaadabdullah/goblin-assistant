export interface TextCostEstimate {
  estimated_tokens: number;
  estimated_cost_usd: number;
}

// Conservative default for "quick estimate" in the UI.
// Interpreted as USD per 1k tokens.
const DEFAULT_USD_PER_1K_TOKENS = 0.02;

export function estimateFromText(text: string): TextCostEstimate {
  const cleaned = (text || '').trim();
  if (!cleaned) {
    return { estimated_tokens: 0, estimated_cost_usd: 0 };
  }

  // Enhanced heuristic that accounts for different character types
  let charCount = 0;
  let emojiCount = 0;
  let unicodeCount = 0;

  // Basic character type counting
  for (const char of cleaned) {
    const code = char.charCodeAt(0);

    // Emoji detection (approximate ranges)
    if (
      (code >= 0x1f300 && code <= 0x1f9ff) || // Emoji blocks
      (code >= 0x2600 && code <= 0x27bf) || // Misc symbols
      (code >= 0x1f600 && code <= 0x1f64f) // Emoticons
    ) {
      emojiCount++;
    }
    // Non-ASCII Unicode
    else if (code > 127) {
      unicodeCount++;
    }
    // Regular ASCII
    else {
      charCount++;
    }
  }

  // Token estimation with better handling for different character types
  // ASCII: ~4 chars per token
  // Unicode: ~2 chars per token (more compact in tokenization)
  // Emoji: ~2 tokens per emoji (often split into multiple tokens)
  const estimatedTokens = Math.max(
    8,
    Math.round(charCount / 4 + unicodeCount / 2 + emojiCount * 2),
  );

  const estimatedCostUsd = (estimatedTokens / 1000) * DEFAULT_USD_PER_1K_TOKENS;

  // Validate numeric results
  const validTokens =
    !isNaN(estimatedTokens) && isFinite(estimatedTokens) ? estimatedTokens : 0;
  const validCost =
    !isNaN(estimatedCostUsd) && isFinite(estimatedCostUsd)
      ? estimatedCostUsd
      : 0;

  return {
    estimated_tokens: validTokens,
    estimated_cost_usd: Number(validCost.toFixed(6)),
  };
}
