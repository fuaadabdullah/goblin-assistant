describe('analytics', () => {
  let originalWindow: typeof window;

  beforeEach(() => {
    jest.resetModules();
    // Clean up any script tags from previous tests
    document.querySelectorAll('script[src*="googletagmanager"]').forEach((s) => s.remove());
    delete (window as Record<string, unknown>).dataLayer;
    delete (window as Record<string, unknown>).gtag;
  });

  describe('initGA', () => {
    it('does nothing when gaMeasurementId is not set', () => {
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { initGA } = require('../analytics');
      initGA();
      expect(document.querySelector('script[src*="googletagmanager"]')).toBeNull();
    });

    it('adds script tag when measurement ID is set', () => {
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST123' } }));
      const { initGA } = require('../analytics');
      initGA();
      const script = document.querySelector('script[src*="googletagmanager"]');
      expect(script).not.toBeNull();
      expect(script?.getAttribute('src')).toContain('G-TEST123');
    });

    it('sets up window.dataLayer', () => {
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST456' } }));
      const { initGA } = require('../analytics');
      initGA();
      expect(window.dataLayer).toEqual(expect.any(Array));
    });

    it('sets up window.gtag function', () => {
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: 'G-TEST789' } }));
      const { initGA } = require('../analytics');
      initGA();
      expect(typeof window.gtag).toBe('function');
    });

    it('does not initialize twice', () => {
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: 'G-ONCE' } }));
      const { initGA } = require('../analytics');
      initGA();
      initGA();
      const scripts = document.querySelectorAll('script[src*="googletagmanager"]');
      expect(scripts).toHaveLength(1);
    });
  });

  describe('trackEvent', () => {
    it('calls window.gtag when available', () => {
      const mockGtag = jest.fn();
      window.gtag = mockGtag;
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { trackEvent } = require('../analytics');
      trackEvent('click', { category: 'button' });
      expect(mockGtag).toHaveBeenCalledWith('event', 'click', { category: 'button' });
    });

    it('does nothing when gtag is not available', () => {
      delete (window as Record<string, unknown>).gtag;
      jest.mock('../../config/env', () => ({ env: { gaMeasurementId: '' } }));
      const { trackEvent } = require('../analytics');
      // Should not throw
      expect(() => trackEvent('click')).not.toThrow();
    });
  });
});
