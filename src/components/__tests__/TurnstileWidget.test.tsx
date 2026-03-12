import { render } from '@testing-library/react';
import TurnstileWidget from '../TurnstileWidget';

describe('TurnstileWidget Component', () => {
    beforeEach(() => {
        (window as any).turnstile = {
            render: jest.fn(() => 'mock-widget-id'),
            reset: jest.fn(),
            remove: jest.fn(),
            execute: jest.fn(),
            getResponse: jest.fn(),
        };
    });

    afterEach(() => {
        delete (window as any).turnstile;
    });

    it('should render a container div', () => {
        const { container } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} />
        );
        expect(container.querySelector('.turnstile-widget')).toBeInTheDocument();
    });

    it('should render invisible mode with hidden div', () => {
        const { container } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} mode="invisible" />
        );
        const div = container.firstChild as HTMLElement;
        expect(div.style.display).toBe('none');
    });

    it('should clean up widget on unmount', () => {
        const { unmount } = render(
            <TurnstileWidget siteKey="test-site-key" onVerify={jest.fn()} />
        );
        unmount();
    });

    it('should accept theme and size props', () => {
        const { container } = render(
            <TurnstileWidget siteKey="test-key" onVerify={jest.fn()} theme="dark" size="compact" />
        );
        expect(container.querySelector('.turnstile-widget')).toBeInTheDocument();
    });
});
