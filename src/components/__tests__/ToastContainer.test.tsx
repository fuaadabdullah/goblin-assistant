import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToastItem } from '../ToastItem';

const baseToast = { id: '1', title: 'Test toast', type: 'info' as const };

describe('ToastItem Component', () => {
    it('renders toast title', () => {
        render(<ToastItem toast={baseToast} onRemove={jest.fn()} />);
        expect(screen.getByText('Test toast')).toBeInTheDocument();
    });

    it('renders toast message when provided', () => {
        render(<ToastItem toast={{ ...baseToast, message: 'Details here' }} onRemove={jest.fn()} />);
        expect(screen.getByText('Details here')).toBeInTheDocument();
    });

    it('calls onRemove when dismiss button clicked', () => {
        const onRemove = jest.fn();
        render(<ToastItem toast={baseToast} onRemove={onRemove} />);
        fireEvent.click(screen.getByLabelText('Dismiss notification'));
        expect(onRemove).toHaveBeenCalledWith('1');
    });

    it('renders success type toast', () => {
        render(<ToastItem toast={{ ...baseToast, type: 'success' }} onRemove={jest.fn()} />);
        expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders error type toast with assertive aria-live', () => {
        const { container } = render(<ToastItem toast={{ ...baseToast, type: 'error' }} onRemove={jest.fn()} />);
        expect(container.querySelector('[aria-live="assertive"]')).toBeInTheDocument();
    });

    it('renders warning type toast', () => {
        render(<ToastItem toast={{ ...baseToast, type: 'warning' }} onRemove={jest.fn()} />);
        expect(screen.getByRole('status')).toBeInTheDocument();
    });
});
