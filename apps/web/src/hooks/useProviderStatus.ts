/**
 * Subscribes to live provider health via Supabase Realtime.
 *
 * The backend upserts provider_status after each health-monitor cycle
 * (every 30 s) and after explicit health probes. This hook replaces the
 * 10-15 s HTTP polling previously done by useRoutingHealth.
 */
import { useEffect, useRef, useState } from 'react';
import { supabase, supabaseConfigured } from '../lib/supabase';
import type { ProviderStatusRow } from '../lib/supabase';
type RealtimeChannel = ReturnType<typeof supabase.channel>;

export type ProviderStatusMap = Record<string, ProviderStatusRow>;

export interface UseProviderStatusResult {
  /** Current snapshot of all known provider health rows, keyed by provider name */
  statuses: ProviderStatusMap;
  /** True while the initial fetch is in flight */
  isLoading: boolean;
  /** Any error that occurred during initial fetch */
  error: Error | null;
  /** True once the Realtime channel is connected */
  connected: boolean;
}

export function useProviderStatus(): UseProviderStatusResult {
  const [statuses, setStatuses] = useState<ProviderStatusMap>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [connected, setConnected] = useState(false);
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    if (!supabaseConfigured) {
      setIsLoading(false);
      return;
    }

    // Initial fetch — populate state before the first Realtime event arrives
    supabase
      .from('provider_status')
      .select('*')
      .then(({ data, error: fetchError }: { data: ProviderStatusRow[] | null; error: { message: string } | null }) => {
        if (fetchError) {
          setError(new Error(fetchError.message));
        } else if (data) {
          const map: ProviderStatusMap = {};
          data.forEach((row) => {
            map[row.provider] = row;
          });
          setStatuses(map);
        }
        setIsLoading(false);
      });

    // Realtime subscription — UPDATE and INSERT events on provider_status
    const channel = supabase
      .channel('provider_status_changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'provider_status' },
        (payload) => {
          const row = (payload.new ?? payload.old) as ProviderStatusRow | undefined;
          if (!row?.provider) return;
          setStatuses((prev) => ({ ...prev, [row.provider]: row }));
        }
      )
      .subscribe((status) => {
        setConnected(status === 'SUBSCRIBED');
      });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, []);

  return { statuses, isLoading, error, connected };
}
