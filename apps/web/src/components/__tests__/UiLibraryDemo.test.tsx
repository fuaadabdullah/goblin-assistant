import { render } from '@testing-library/react';
import { UiLibraryDemo } from '../UiLibraryDemo';

describe('UiLibraryDemo Component', () => {
    it('should render UI library demo', () => {
        const { container } = render(<UiLibraryDemo />);
        expect(container).toBeInTheDocument();
    });

    it('should display buttons', () => {
        const { getByText } = render(<UiLibraryDemo />);
        expect(getByText('Default Button')).toBeInTheDocument();
        expect(getByText('Secondary')).toBeInTheDocument();
    });

    it('should render without errors', () => {
        const { container } = render(<UiLibraryDemo />);
        expect(container.firstChild).toBeTruthy();
    });
});
