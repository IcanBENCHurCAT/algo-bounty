'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useWallet } from '@/hooks/useWallet';
import { getBounties, getMyProfile, markNotificationRead, type AgentProfile, type Bounty, type NotificationItem } from '@/lib/api';
import WalletConnect from '@/components/WalletConnect';
import BountyCard from '@/components/BountyCard';

export default function ProfilePage() {
  const router = useRouter();
  const { connected, address, jwt, profile, karma } = useWallet();
  const [profileData, setProfileData] = useState<AgentProfile | null>(null);
  const [bounties, setBounties] = useState<Bounty[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'overview' | 'bounties' | 'notifications'>('overview');
  const [notifLoading, setNotifLoading] = useState(false);

  const loadProfile = useCallback(async () => {
    if (!jwt || !address) return;
    try {
      const data = await getMyProfile(jwt);
      setProfileData(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load profile');
    }
  }, [jwt, address]);

  const loadBounties = useCallback(async () => {
    if (!connected || !address) return;
    try {
      const res = await getBounties({ page: 1, limit: 50, worker: address });
      setBounties(res.bounties);
    } catch (err: unknown) {
      console.error('Failed to load bounties:', err);
    }
  }, [connected, address]);

  const loadNotifications = useCallback(async () => {
    if (!jwt) return;
    setNotifLoading(true);
    try {
      const data = await getNotifications(jwt);
      setNotifications(data);
      setNotifLoading(false);
    } catch (err: unknown) {
      console.error('Failed to load notifications:', err);
      setNotifLoading(false);
    }
  }, [jwt]);

  useEffect(() => {
    if (connected && address) {
      setLoading(true);
      Promise.all([loadProfile(), loadBounties()]).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [connected, address, loadProfile, loadBounties]);

  useEffect(() => {
    if (tab === 'notifications' && connected) {
      loadNotifications();
    }
  }, [tab, connected, loadNotifications]);

  // Use hook-level karma if backend profile not loaded yet
  const displayKarma = profileData?.karma ?? karma ?? 0;

  const getTierBadge = (k: number) => {
    if (k >= 100) return { label: 'Expert', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50' };
    if (k >= 25) return { label: 'Journey', color: 'bg-blue-500/20 text-blue-400 border-blue-500/50' };
    return { label: 'Novice', color: 'bg-gray-500/20 text-gray-400 border-gray-500/50' };
  };

  const tier = getTierBadge(displayKarma);

  const handleRefresh = () => {
    loadProfile();
    loadBounties();
  };

  const unreadCount = notifications.filter(n => !n.read).length;

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
          <h1 className="text-3xl font-bold mb-6">My Profile</h1>
          <p className="text-gray-400 mb-8">Connect your wallet to view your profile and activity.</p>
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
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              My Profile
            </h1>
            <div className="flex items-center gap-4">
              <WalletConnect variant="compact" />
              <button
                onClick={handleRefresh}
                className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
                title="Refresh"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mt-4">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'bounties', label: `My Bounties (${bounties.length})` },
              { key: 'notifications', label: `Notifications${unreadCount > 0 ? ` (${unreadCount})` : ''}` },
            ].map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key as typeof tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === t.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {tab === 'overview' && (
          <div className="space-y-6">
            {/* Karma Card */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Reputation</h2>
                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${tier.color}`}>
                  {tier.label}
                </span>
              </div>
              <div className="text-5xl font-bold text-blue-400 mb-2">{displayKarma}</div>
              <p className="text-gray-500 text-sm">
                {displayKarma < 25 && 'Complete bounties to level up. Next tier at 25 karma.'}
                {displayKarma >= 25 && displayKarma < 100 && 'Great progress! Next tier at 100 karma (Expert).'}
                {displayKarma >= 100 && 'Maximum reputation reached! You are an Expert.'}
              </p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Bounties Created', value: profileData?.bounties_created ?? 0, icon: '📝' },
                { label: 'Bounties Completed', value: profileData?.bounties_completed ?? 0, icon: '✅' },
                { label: 'Disputes Won', value: profileData?.disputes_won ?? 0, icon: '🏆' },
                { label: 'Disputes Lost', value: profileData?.disputes_lost ?? 0, icon: '⚠️' },
              ].map(stat => (
                <div key={stat.label} className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center">
                  <div className="text-2xl mb-1">{stat.icon}</div>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-gray-500 text-sm">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Address */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">Wallet Address</h3>
              <div className="flex items-center gap-2">
                <code className="text-blue-400 text-sm break-all flex-1">
                  {address?.slice(0, 6)}...{address?.slice(-4)}
                </code>
                <button
                  onClick={() => navigator.clipboard.writeText(address || '')}
                  className="text-gray-400 hover:text-white transition-colors"
                  title="Copy address"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
              {address && (
                <a
                  href={`https://algoexplorer.io/address/${address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-sm mt-1 inline-block"
                >
                  View on AlgoExplorer →
                </a>
              )}
            </div>
          </div>
        )}

        {tab === 'bounties' && (
          <div>
            {bounties.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <p className="text-lg mb-2">No bounties yet</p>
                <button
                  onClick={() => router.push('/create')}
                  className="text-blue-400 hover:text-blue-300"
                >
                  Create your first bounty →
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {bounties.map(bounty => (
                  <div key={bounty.id} className="cursor-pointer" onClick={() => router.push(`/bounties/${bounty.bounty_id}`)}>
                    <BountyCard bounty={bounty} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'notifications' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Notifications</h3>
              {notifications.length > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Mark all read
                </button>
              )}
            </div>
            {notifLoading ? (
              <div className="text-center py-8 text-gray-500">
                <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                <p>Loading...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No notifications</p>
              </div>
            ) : (
              <div className="space-y-2">
                {notifications.map(n => (
                  <div
                    key={n.id}
                    className={`p-4 rounded-lg border transition-colors cursor-pointer ${
                      n.read ? 'bg-gray-900/50 border-gray-800' : 'bg-gray-900 border-blue-500/30'
                    }`}
                    onClick={() => handleMarkRead(n.notification_id)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className={!n.read ? 'text-white font-medium' : 'text-gray-300'}>
                          {n.message || n.type}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {n.created_at ? new Date(n.created_at * 1000).toLocaleString() : ''}
                        </p>
                      </div>
                      {!n.read && (
                        <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
