import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api';
import { queryKeys } from '../../lib/query-keys';
import { persistAuthSession } from '../../utils/auth-session';
import { PasskeyChallenge, PasskeyVerificationChallenge, LoginResponse } from '../../types/api';

interface PasskeyPanelProps {
  email: string;
  onSuccess: () => void;
  // eslint-disable-next-line no-unused-vars
  onError: (message: string) => void;
}

// Type for WebAuthn PublicKeyCredentialCreationOptions challenge fields
interface WebAuthnCreationPublicKey {
  challenge: string | Uint8Array;
  rp: { name: string; id: string };
  user: { id: string | Uint8Array; name: string; displayName: string };
  pubKeyCredParams: Array<{ type: string; alg: number }>;
  timeout?: number;
  attestation?: string;
  authenticatorSelection?: {
    authenticatorAttachment?: string;
    requireResidentKey?: boolean;
    userVerification?: string;
  };
}

// Type for WebAuthn PublicKeyCredentialRequestOptions challenge fields
interface WebAuthnRequestPublicKey {
  challenge: string | Uint8Array;
  rpId?: string;
  allowCredentials?: Array<{ type: string; id: string | Uint8Array }>;
  timeout?: number;
  userVerification?: string;
}

// Helper: base64url decode
function base64urlToUint8Array(base64url: string): Uint8Array {
  const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
  const raw = window.atob(base64);
  const array = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) array[i] = raw.charCodeAt(i);
  return array;
}

// Helper: convert credential to JSON friendly object
function credentialToJSON(cred: any): any {
  if (!cred) return null;
  const credentialData: any = { id: cred.id, type: cred.type };
  if (cred.rawId) credentialData.rawId = btoa(String.fromCharCode(...new Uint8Array(cred.rawId)));
  if (cred.response) {
    credentialData.response = {};
    const resp = cred.response;
    ['attestationObject', 'clientDataJSON', 'authenticatorData', 'signature', 'userHandle'].forEach(
      k => {
        if (resp[k]) credentialData.response[k] = btoa(String.fromCharCode(...new Uint8Array(resp[k])));
      }
    );
  }
  return credentialData;
}

function isPasskeyRegistrationChallenge(
  data: PasskeyChallenge | PasskeyVerificationChallenge
): data is PasskeyChallenge {
  return Boolean(
    data.publicKey &&
    'rp' in data.publicKey &&
    'user' in data.publicKey &&
    'pubKeyCredParams' in data.publicKey &&
    Array.isArray(data.publicKey.pubKeyCredParams)
  );
}

function isPasskeyVerificationChallenge(
  data: PasskeyChallenge | PasskeyVerificationChallenge
): data is PasskeyVerificationChallenge {
  return Boolean(
    data.publicKey &&
    ('rpId' in data.publicKey || 'allowCredentials' in data.publicKey)
  );
}

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
      if (!('PublicKeyCredential' in window))
        throw new Error('WebAuthn not supported in this browser');
      const challengeData =
        (await apiClient.passkeyChallenge(email)) as PasskeyChallenge | PasskeyVerificationChallenge;
      if (!isPasskeyRegistrationChallenge(challengeData)) {
        throw new Error('Invalid passkey registration challenge');
      }
      const publicKey: WebAuthnCreationPublicKey = { ...challengeData.publicKey };

      // Decode base64url fields
      if (publicKey.challenge) publicKey.challenge = base64urlToUint8Array(publicKey.challenge as string);
      if (publicKey.user && publicKey.user.id)
        publicKey.user.id = base64urlToUint8Array(publicKey.user.id as string);

      const credential: any = await navigator.credentials.create({
        publicKey: publicKey as unknown as PublicKeyCredentialCreationOptions,
      });
      const jsonCred = credentialToJSON(credential);
      await apiClient.passkeyRegister(email, jsonCred);
      setStatus('Passkey registered');
      onSuccess();
    } catch (e: any) {
      onError(e.message || 'Passkey registration failed');
    } finally {
      setRegistering(false);
    }
  };

  const handleAuth = async () => {
    if (!ensureEmail() || authenticating) return;
    setAuthenticating(true);
    setStatus(null);
    try {
      if (!('PublicKeyCredential' in window))
        throw new Error('WebAuthn not supported in this browser');
      const challengeData =
        (await apiClient.passkeyChallenge(email)) as PasskeyChallenge | PasskeyVerificationChallenge;
      if (!isPasskeyVerificationChallenge(challengeData)) {
        throw new Error('Invalid passkey verification challenge');
      }
      const publicKey: WebAuthnRequestPublicKey = { ...challengeData.publicKey };
      if (publicKey.challenge) publicKey.challenge = base64urlToUint8Array(publicKey.challenge as string);
      // allowCredentials id decode
      if (Array.isArray(publicKey.allowCredentials)) {
        publicKey.allowCredentials = publicKey.allowCredentials.map((c) => ({
          ...c,
          id: base64urlToUint8Array(c.id as string),
        }));
      }
      const assertion: any = await navigator.credentials.get({
        publicKey: publicKey as unknown as PublicKeyCredentialRequestOptions,
      });
      const jsonAssertion = credentialToJSON(assertion);
      const authResponse = await apiClient.passkeyAuth(email, jsonAssertion) as LoginResponse;
      const tokenValue = authResponse.access_token || null;
      if (!tokenValue) {
        throw new Error('Authentication failed - invalid server response');
      }
      persistAuthSession({
        token: tokenValue,
        user: authResponse.user,
        expiresIn: authResponse.expires_in,
      });
      queryClient.setQueryData(queryKeys.authValidate, {
        token: tokenValue,
        user: authResponse.user,
        isAuthenticated: true,
        isHydrated: true,
      });
      setStatus('Passkey authentication successful');
      onSuccess();
    } catch (e: any) {
      onError(e.message || 'Passkey authentication failed');
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
