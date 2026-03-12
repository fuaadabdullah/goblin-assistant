import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import SocialLoginButtons from '../SocialLoginButtons';

describe('SocialLoginButtons', () => {
  const onGoogleLogin = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders Google login button', () => {
    render(<SocialLoginButtons onGoogleLogin={onGoogleLogin} />);
    expect(screen.getByText('Continue with Google')).toBeInTheDocument();
  });

  it('calls onGoogleLogin when clicked', () => {
    render(<SocialLoginButtons onGoogleLogin={onGoogleLogin} />);
    fireEvent.click(screen.getByText('Continue with Google'));
    expect(onGoogleLogin).toHaveBeenCalled();
  });

  it('disables button when isLoading', () => {
    render(<SocialLoginButtons onGoogleLogin={onGoogleLogin} isLoading />);
    expect(screen.getByText('Continue with Google').closest('button')).toBeDisabled();
  });

  it('enables button when not loading', () => {
    render(<SocialLoginButtons onGoogleLogin={onGoogleLogin} />);
    expect(screen.getByText('Continue with Google').closest('button')).not.toBeDisabled();
  });

  it('renders Google SVG icon', () => {
    const { container } = render(<SocialLoginButtons onGoogleLogin={onGoogleLogin} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});
