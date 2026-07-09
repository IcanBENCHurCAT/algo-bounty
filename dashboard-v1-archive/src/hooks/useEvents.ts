import { useEffect, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export type MarketplaceEvent = {
  event_type: string;
  data: Record<string, unknown>;
};

export function useEvents(onEvent: (event: MarketplaceEvent) => void) {
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/api/v1/events`);

    // Generic events we care about
    const eventTypes = [
      'bounty.created',
      'bounty.claimed',
      'bounty.submitted',
      'bounty.approved',
      'bounty.rejected',
      'bounty.disputed',
      'karma.updated'
    ];

    const listeners = eventTypes.map(type => {
      const listener = (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onEventRef.current({ event_type: type, data });
        } catch (err) {
          console.error(`Failed to parse SSE data for ${type}:`, err);
        }
      };
      eventSource.addEventListener(type, listener);
      return { type, listener };
    });

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      eventSource.close();
    };

    return () => {
      listeners.forEach(({ type, listener }) => {
        eventSource.removeEventListener(type, listener);
      });
      eventSource.close();
    };
  }, []);
}
