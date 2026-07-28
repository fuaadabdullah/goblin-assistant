import { useEffect } from 'react';
import { supabase, supabaseConfigured } from '@/lib/supabase';

interface RealtimePayload {
  eventType: 'INSERT' | 'UPDATE' | 'DELETE';
  new: any;
  old: any;
}

export function useSupabaseRealtime(
  tableName: string,
  onPayload?: (payload: RealtimePayload) => void
) {
  useEffect(() => {
    if (!supabaseConfigured) {
      return;
    }

    const channel = supabase
      .channel(`public.${tableName}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: tableName,
        },
        (payload: any) => {
          onPayload?.(payload as RealtimePayload);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [tableName, onPayload]);
}
