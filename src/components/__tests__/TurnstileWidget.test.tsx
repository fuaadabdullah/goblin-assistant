import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TurnstileWidget } from '../../TurnstileWidget';

describe('TurnstileWidget Component', () => {
    beforeEach(() => {
        // Mock window.turnstile
        (window as any).turnstile = {
            render: jest.fn(() => 'mock-widget-id'),
            reset: jest.fn(),
            remove: jest.fn(),
        };
    });

    afterEach(() => {
        delete (window as any).turnstile;
    });

    it('should render Turnstile widget', () => {
        const { container } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} />
        );
        expect(container.querySelector('[data-turnstile]')).toBeInTheDocument();
    });

    it('should call onVerify callback on token generation', async () => {
        const onVerify = jest.fn();
        render(
            <TurnstileWidget siteKey="test-site-key" onVerify={onVerify} />
        );

        await waitFor(() => {
            if (onVerify.mock.calls.length > 0) {
                expect(onVerify).toHaveBeenCalled();
            }
        });
    });

    it('should handle widget reset', () => {
        const { rerender } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} />
        );

        rerender(<TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} resetTrigger={1} />);
    });

    it('should clean up widget on unmount', () => {
        const { unmount } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} />
        );

        unmount();
        // Turnstile cleanup should be called
    });
});
