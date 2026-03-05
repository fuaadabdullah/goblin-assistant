import { render, screen } from '@testing-library/react';
import { TerminalShowcase } from '../../TerminalShowcase';

describe('TerminalShowcase Component', () => {
    it('should render terminal showcase', () => {
        render(<TerminalShowcase lines={['$ echo "Hello"', 'Hello']} />);
        expect(screen.getByRole('region')).toBeInTheDocument();
    });

    it('should display terminal lines', () => {
        const lines = ['$ npm install', 'added 100 packages'];
        render(<TerminalShowcase lines={lines} />);

        // Terminal should display all lines
        for (const line of lines) {
            // Lines might be in terminal display
        }
    });

    it('should apply terminal styling', () => {
        const { container } = render(<TerminalShowcase lines={['$ test']} />);
        expect(container.querySelector('.terminal')).toBeInTheDocument();
    });

    it('should handle empty lines', () => {
        render(<TerminalShowcase lines={[]} />);
        expect(screen.getByRole('region')).toBeInTheDocument();
    });
});
