describe('analytics', () => {
  beforeEach(() => {
    vi.resetModules();
    document.querySelectorAll('script[src*="googletagmanager"]').forEach((s) => s.remove());
    delete (window as Record<string, unknown>).dataLayer;
    delete (window as Record<string, unknown>).gtag;
  });

  describe('initGA', () => {
    it('does nothing when gaMeasurementId is not set', async () => {
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { initGA } = await import('../analytics');
      initGA();
      expect(document.querySelector('script[src*="googletagmanager"]')).toBeNull();
    });

    it('adds script tag when measurement ID is set', async () => {
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST123' } }));
      const { initGA } = await import('../analytics');
      initGA();
      const script = document.querySelector('script[src*="googletagmanager"]');
      expect(script).not.toBeNull();
      expect(script?.getAttribute('src')).toContain('G-TEST123');
    });

    it('sets up window.dataLayer', async () => {
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST456' } }));
      const { initGA } = await import('../analytics');
      initGA();
      expect(window.dataLayer).toEqual(expect.any(Array));
    });

    it('sets up window.gtag function', async () => {
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST789' } }));
      const { initGA } = await import('../analytics');
      initGA();
      expect(typeof window.gtag).toBe('function');
    });

    it('does not initialize twice', async () => {
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: 'G-ONCE' } }));
      const { initGA } = await import('../analytics');
      initGA();
      initGA();
      const scripts = document.querySelectorAll('script[src*="googletagmanager"]');
      expect(scripts).toHaveLength(1);
    });
  });

  describe('trackEvent', () => {
    it('calls window.gtag when available', async () => {
      const mockGtag = vi.fn();
      window.gtag = mockGtag;
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { trackEvent } = await import('../analytics');
      trackEvent('click', { category: 'button' });
      expect(mockGtag).toHaveBeenCalledWith('event', 'click', { category: 'button' });
    });

    it('does nothing when gtag is not available', async () => {
      delete (window as Record<string, unknown>).gtag;
      vi.doMock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { trackEvent } = await import('../analytics');
      expect(() => trackEvent('click')).not.toThrow();
    });
  });
});
