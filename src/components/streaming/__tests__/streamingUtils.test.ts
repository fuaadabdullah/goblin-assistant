import { getNewChunk, toTokenChunk } from '../streamingUtils';

describe('streamingUtils', () => {
  describe('getNewChunk', () => {
    it('returns the remaining text when current starts with previous', () => {
      expect(getNewChunk('Hello', 'Hello world')).toBe(' world');
    });

    it('returns full current text when it does not start with previous', () => {
      expect(getNewChunk('abc', 'xyz')).toBe('xyz');
    });

    it('returns empty string when texts are identical', () => {
      expect(getNewChunk('same', 'same')).toBe('');
    });

    it('handles empty previous text', () => {
      expect(getNewChunk('', 'Hello')).toBe('Hello');
    });

    it('handles empty current text', () => {
      expect(getNewChunk('Hello', '')).toBe('');
    });
  });

  describe('toTokenChunk', () => {
    it('creates a non-code chunk for regular text', () => {
      const chunk = toTokenChunk('hello', 'some text');
      expect(chunk.text).toBe('hello');
      expect(chunk.isCode).toBe(false);
      expect(chunk.index).toBe('some text'.length);
    });

    it('detects triple backtick as code', () => {
      const chunk = toTokenChunk('```js\nconsole.log()', '');
      expect(chunk.isCode).toBe(true);
    });

    it('detects single backtick as code', () => {
      const chunk = toTokenChunk('`code`', '');
      expect(chunk.isCode).toBe(true);
    });

    it('handles whitespace-padded chunks', () => {
      const chunk = toTokenChunk('  ```python', '');
      expect(chunk.isCode).toBe(true);
    });

    it('non-code chunk for plain text', () => {
      const chunk = toTokenChunk('just words', 'previous');
      expect(chunk.isCode).toBe(false);
    });
  });
});
