import { renderHook, act } from '@testing-library/react';

jest.mock('../../api', () => ({
  saveProfile: jest.fn(),
  savePreferences: jest.fn(),
}));

import { useAccountProfile } from '../useAccountProfile';
import { saveProfile, savePreferences } from '../../api';

const mockSaveProfile = saveProfile as jest.Mock;
const mockSavePreferences = savePreferences as jest.Mock;

describe('useAccountProfile', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSaveProfile.mockResolvedValue(undefined);
    mockSavePreferences.mockResolvedValue(undefined);
  });

  it('initializes with user name', () => {
    const { result } = renderHook(() => useAccountProfile({ name: 'Alice', email: 'a@b.com' }));
    expect(result.current.name).toBe('Alice');
    expect(result.current.email).toBe('a@b.com');
  });

  it('defaults to empty strings without user', () => {
    const { result } = renderHook(() => useAccountProfile(null));
    expect(result.current.name).toBe('');
    expect(result.current.email).toBe('');
  });

  it('starts with default preferences', () => {
    const { result } = renderHook(() => useAccountProfile(null));
    expect(result.current.preferences).toEqual({
      summaries: true,
      notifications: true,
      familyMode: false,
    });
  });

  it('toggles a preference', () => {
    const { result } = renderHook(() => useAccountProfile(null));
    act(() => result.current.togglePreference('familyMode'));
    expect(result.current.preferences.familyMode).toBe(true);
  });

  it('sets name', () => {
    const { result } = renderHook(() => useAccountProfile(null));
    act(() => result.current.setName('Bob'));
    expect(result.current.name).toBe('Bob');
  });

  it('handleSave calls saveProfile and savePreferences', async () => {
    const { result } = renderHook(() => useAccountProfile({ name: 'X', email: 'x@y.com' }));
    const fakeEvent = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSave(fakeEvent); });
    expect(mockSaveProfile).toHaveBeenCalled();
    expect(mockSavePreferences).toHaveBeenCalled();
  });

  it('sets saved to true on success', async () => {
    const { result } = renderHook(() => useAccountProfile(null));
    const fakeEvent = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSave(fakeEvent); });
    expect(result.current.saved).toBe(true);
  });

  it('sets error on failure', async () => {
    mockSaveProfile.mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useAccountProfile(null));
    const fakeEvent = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSave(fakeEvent); });
    expect(result.current.error).toBeTruthy();
  });

  it('sets saving during save', async () => {
    let resolve: () => void;
    mockSaveProfile.mockImplementation(() => new Promise(r => { resolve = r; }));
    mockSavePreferences.mockResolvedValue(undefined);
    const { result } = renderHook(() => useAccountProfile(null));
    const fakeEvent = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    let promise: Promise<void>;
    act(() => { promise = result.current.handleSave(fakeEvent); });
    expect(result.current.saving).toBe(true);
    await act(async () => { resolve!(); await promise!; });
    expect(result.current.saving).toBe(false);
  });
});
