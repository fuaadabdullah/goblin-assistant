import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  browserSupportsWebAuthn,
  startAuthentication,
  startRegistration,
} from '@simplewebauthn/browser';
import type {
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
} from '@simplewebauthn/browser';
import { apiClient } from '@/lib/api';
import { snapshotFromSupabaseSession } from '@/lib/auth-state';
import { supabase } from '@/lib/supabase';
import { getUserMessage } from '@/lib/error/toast';
import { queryKeys } from '../../lib/query-keys';

interface PasskeyPanelProps {
  email: string;
  onSuccess: () => void;
  onError: (message: string) => void;
}

type PasskeyOptions =
  | { publicKey: PublicKeyCredentialCreationOptionsJSON }
  | { publicKey: PublicKeyCredentialRequestOptionsJSON };

const isAuthenticationOptions = (
  options: PasskeyOptions
): options is { publicKey: PublicKeyCredentialRequestOptionsJSON } =>
  'allowCredentials' in options.publicKey;

const PasskeyPanel: React.FC<PasskeyPanelProps> = ({ email, onSuccess, onError }) => {
  const [registering, setRegistering] = useState(false);
  const [authenticating, setAuthenticating] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const ensureEmail = () => {
    if (!email) {
      onError('Enter email above before using passkey');
      return false;
    }
    return true;
  };

  const handleRegister = async () => {
    if (!ensureEmail() || registering) return;
    setRegistering(true);
    setStatus(null);
    try {
      if (!browserSupportsWebAuthn())
        throw new Error('WebAuthn not supported in this browser');

      const options = (await apiClient.passkeyChallenge(email)) as PasskeyOptions;
      if (isAuthenticationOptions(options)) {
        throw new Error('This account already has a passkey registered');
      }

      const credential = await startRegistration({ optionsJSON: options.publicKey });
      await apiClient.passkeyRegister(email, credential);
      setStatus('Passkey registered');
      onSuccess();
    } catch (e) {
      onError(getUserMessage(e) || 'Passkey registration failed');
    } finally {
      setRegistering(false);
    }
  };

  const handleAuth = async () => {
    if (!ensureEmail() || authenticating) return;
    setAuthenticating(true);
    setStatus(null);
    try {
      if (!browserSupportsWebAuthn())
        throw new Error('WebAuthn not supported in this browser');

      const options = (await apiClient.passkeyChallenge(email)) as PasskeyOptions;
      if (!isAuthenticationOptions(options)) {
        throw new Error('No passkey registered for this account');
      }

      const assertion = await startAuthentication({ optionsJSON: options.publicKey });
      const { token_hash } = await apiClient.passkeyAuth(email, assertion);
      if (!token_hash) {
        throw new Error('Authentication failed - invalid server response');
      }

      const { data, error } = await supabase.auth.verifyOtp({
        token_hash,
        type: 'magiclink',
      });
      if (error || !data.session) {
        throw error ?? new Error('Unable to establish a session');
      }

      queryClient.setQueryData(
        queryKeys.authValidate,
        snapshotFromSupabaseSession(data.session)
      );
      setStatus('Passkey authentication successful');
      onSuccess();
    } catch (e) {
      onError(getUserMessage(e) || 'Passkey authentication failed');
    } finally {
      setAuthenticating(false);
    }
  };

  return (
    <div className="bg-surface-hover border border-border rounded-lg p-4 text-sm w-full">
      <p className="text-muted mb-2">Passkey (WebAuthn) login:</p>
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={handleRegister}
          disabled={registering}
          className="flex-1 bg-accent hover:bg-accent-hover disabled:opacity-50 px-3 py-2 rounded text-text-inverse shadow-glow-accent transition-colors"
        >
          {registering ? 'Registering…' : 'Register Passkey'}
        </button>
        <button
          type="button"
          onClick={handleAuth}
          disabled={authenticating}
          className="flex-1 bg-primary hover:bg-primary-hover disabled:opacity-50 px-3 py-2 rounded text-text-inverse shadow-glow-primary transition-colors"
        >
          {authenticating ? 'Authenticating…' : 'Authenticate'}
        </button>
      </div>
      {status && <p className="mt-3 text-success text-xs">{status}</p>}
    </div>
  );
};

export default PasskeyPanel;
