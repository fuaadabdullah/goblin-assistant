import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../AccountProfileForm', () => {
  return function MockProfileForm(props: { name: string; email: string }) {
    return <div data-testid="profile-form">{props.name} – {props.email}</div>;
  };
});

jest.mock('../AccountPreferences', () => {
  return function MockPreferences() {
    return <div data-testid="preferences">Preferences</div>;
  };
});

jest.mock('../AccountBillingCard', () => {
  return function MockBilling() {
    return <div data-testid="billing">Billing</div>;
  };
});

jest.mock('@/components/Seo', () => {
  return function MockSeo(props: { title: string }) {
    return <div data-testid="seo">{props.title}</div>;
  };
});

import AccountView from '../AccountView';

const makeState = (overrides = {}) => ({
  name: 'Fuaad',
  email: 'fuaad@example.com',
  saved: false,
  error: null,
  saving: false,
  setName: jest.fn(),
  handleSave: jest.fn(),
  preferences: {},
  togglePreference: jest.fn(),
  ...overrides,
});

describe('AccountView', () => {
  it('renders the heading', () => {
    render(<AccountView state={makeState() as any} />);
    expect(screen.getByRole('heading', { name: 'Account' })).toBeInTheDocument();
  });

  it('renders the subheading', () => {
    render(<AccountView state={makeState() as any} />);
    expect(screen.getByText(/Manage your profile/)).toBeInTheDocument();
  });

  it('renders Seo component with Account title', () => {
    render(<AccountView state={makeState() as any} />);
    expect(screen.getByTestId('seo')).toHaveTextContent('Account');
  });

  it('passes name and email to profile form', () => {
    render(<AccountView state={makeState({ name: 'Alice', email: 'alice@test.com' }) as any} />);
    expect(screen.getByTestId('profile-form')).toHaveTextContent('Alice');
    expect(screen.getByTestId('profile-form')).toHaveTextContent('alice@test.com');
  });

  it('renders preferences component', () => {
    render(<AccountView state={makeState() as any} />);
    expect(screen.getByTestId('preferences')).toBeInTheDocument();
  });

  it('renders billing component', () => {
    render(<AccountView state={makeState() as any} />);
    expect(screen.getByTestId('billing')).toBeInTheDocument();
  });

  it('has main content area with id', () => {
    render(<AccountView state={makeState() as any} />);
    expect(document.getElementById('main-content')).toBeInTheDocument();
  });
});
