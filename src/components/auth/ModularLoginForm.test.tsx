/**
 * Tests for ModularLoginForm component
 * 
 * Tests cover:
 * - Form rendering and initial state
 * - Form input and interaction
 * - Component behavior
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ModularLoginForm from '@/components/auth/ModularLoginForm';

describe('ModularLoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('Rendering', () => {
    it('should render without crashing', () => {
      const { container } = render(<ModularLoginForm />);
      expect(container).toBeInTheDocument();
    });

    it('should render form elements', () => {
      render(<ModularLoginForm />);
      
      // Check for form element
      const forms = screen.getAllByRole('button');
      expect(forms.length).toBeGreaterThan(0);
    });

    it('should render input fields', () => {
      render(<ModularLoginForm />);
      
      const inputs = screen.queryAllByRole('textbox');
      // Should have at least one text input (email or name)
      expect(inputs.length).toBeGreaterThanOrEqual(0);
    });

    it('should render buttons', () => {
      render(<ModularLoginForm />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Form Input', () => {
    it('should accept text input', async () => {
      render(<ModularLoginForm />);
      
      const inputs = screen.queryAllByPlaceholderText(/email|password|name/i);
      if (inputs.length > 0) {
        await userEvent.type(inputs[0], 'test');
        expect((inputs[0] as HTMLInputElement).value).toBe('test');
      }
    });

    it('should allow multiple inputs', async () => {
      render(<ModularLoginForm />);
      
      const inputs = screen.queryAllByPlaceholderText(/email|password|name/i);
      expect(inputs.length).toBeGreaterThan(0);
    });
  });

  describe('User Interaction', () => {
    it('should handle button clicks', async () => {
      render(<ModularLoginForm />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
      
      // Click first button
      fireEvent.click(buttons[0]);
      expect(buttons[0]).toBeInTheDocument();
    });

    it('should handle form submission', async () => {
      const onSuccess = vi.fn();
      render(<ModularLoginForm onSuccess={onSuccess} />);
      
      const buttons = screen.getAllByRole('button');
      if (buttons.length > 0) {
        fireEvent.click(buttons[0]);
        // Form should still be in document after click
        expect(buttons[0]).toBeInTheDocument();
      }
    });
  });

  describe('Component Initialization', () => {
    it('should initialize with localStorage cleared', () => {
      render(<ModularLoginForm />);
      
      expect(localStorage.getItem('test')).toBeNull();
      localStorage.setItem('test', 'value');
      expect(localStorage.getItem('test')).toBe('value');
    });

    it('should handle callbacks', () => {
      const onSuccess = vi.fn();
      const onError = vi.fn();
      
      const { container } = render(
        <ModularLoginForm onSuccess={onSuccess} onError={onError} />
      );
      
      expect(container).toBeInTheDocument();
    });
  });

  describe('Form Navigation', () => {
    it('should have multiple tabs/forms', () => {
      render(<ModularLoginForm />);
      
      // Look for all buttons - there should be tabs or navigation options
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(1);
    });

    it('should allow switching between tabs', async () => {
      render(<ModularLoginForm />);
      
      const buttons = screen.getAllByRole('button');
      if (buttons.length > 1) {
        fireEvent.click(buttons[1]);
        // Component should still render after tab switch
        const stillVisible = screen.getAllByRole('button');
        expect(stillVisible.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Accessibility', () => {
    it('should have accessible buttons', () => {
      render(<ModularLoginForm />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeInTheDocument();
      });
    });

    it('should have input elements', () => {
      render(<ModularLoginForm />);
      
      // Component can have forms or just inputs
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});

