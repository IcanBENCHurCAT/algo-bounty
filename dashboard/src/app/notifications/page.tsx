'use client';

import { useState, useEffect, useCallback } from 'react';
import { getNotifications, markNotificationRead, type NotificationItem } from '@/lib/api';
import { useWallet } from '@/hooks/useWallet';
import WalletConnect from '@/components/WalletConnect';

export default function NotificationsPage() {
  const { connected, jwt } = useWallet();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    if (!jwt) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await getNotifications(jwt);
      setNotifications(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }, [jwt]);

  useEffect(() => { loadNotifications(); }, [loadNotifications]);

  const handleMarkRead = async (notificationId: number) => {
    if (!jwt) return;
    try {
      await markNotificationRead(notificationId, jwt);
      setNotifications(prev => prev.map(n => n.notification_id === notificationId ? { ...n, read: true } : n));
    } catch { /* silent */ }
  };

  const handleMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  if (!connected) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-8">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-3xl font-bold mb-6">Notifications</h1>
          <p className="text-gray-400 mb-8">Connect your wallet to view your notifications.</p>
          <WalletConnect />
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p>Loading notifications...</p>
        </div>
      </div>
    );
  }

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Notifications
            {unreadCount > 0 && (
              <span className="ml-2 text-sm text-blue-400 font-normal">({unreadCount} unread)</span>
            )}
          </h1>
          {notifications.length > 0 && (
            <button onClick={handleMarkAllRead} className="text-sm text-blue-400 hover:text-blue-300">
              Mark all read
            </button>
          )}
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4 mb-6 text-red-400">
            {error}
          </div>
        )}

        {notifications.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg mb-2">No notifications</p>
            <p className="text-sm">We'll let you know when something happens.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map(n => (
              <div
                key={n.notification_id}
                className={`p-4 rounded-lg border transition-colors cursor-pointer ${
                  n.read
                    ? 'bg-gray-900/50 border-gray-800'
                    : 'bg-gray-900 border-blue-500/30'
                }`}
                onClick={() => handleMarkRead(n.notification_id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className={!n.read ? 'text-white font-medium' : 'text-gray-300'}>
                      {n.event_type?.replace(/_/g, ' ') || n.event_type || 'Event'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                    </p>
                    {n.data && Object.keys(n.data).length > 0 && (
                      <pre className="mt-2 text-xs text-gray-600 bg-gray-950 p-2 rounded overflow-x-auto">
                        {JSON.stringify(n.data, null, 2)}
                      </pre>
                    )}
                  </div>
                  {!n.read && (
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0"></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
