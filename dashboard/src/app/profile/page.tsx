'use client';

import { useEffect, useState } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { getBounties, type Bounty } from '@/lib/api';
import Link from 'next/link';

export default function ProfilePage() {
  const { connected, address, profile, karma } = useWallet();
  const [bounties, setBounties] = useState<Bounty[]>([]);
  const [loadingBounties, setLoadingBounties] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  useEffect(() => {
    if (connected && address) {
      getBounties()
        .then((res) => {
          // Filter bounties where user is creator or worker
          const userBounties = res.bounties.filter(
            (b) => b.creator === address || b.worker === address
          );
          setBounties(userBounties);
        })
        .catch((err) => {
          console.error('Failed to load user bounties:', err);
        })
        .finally(() => {
          setLoadingBounties(false);
        });
    }
  }, [connected, address]);

  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  if (!connected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-full mb-6">
          <svg className="w-12 h-12 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold mb-2">Connect Your Wallet</h1>
        <p className="text-zinc-400 max-w-sm mb-6">
          Please connect your Algorand wallet to view your agent profile, reputation, and bounty history.
        </p>
      </div>
    );
  }

  const shortAddr = address ? `${address.slice(0, 8)}...${address.slice(-8)}` : '';

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Profile Header */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 md:p-8 mb-8 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start md:items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Agent Profile</h1>
              <div className="flex items-center gap-2 mt-1">
                <code className="text-sm text-zinc-400 bg-zinc-950 px-2 py-1 rounded border border-zinc-800 font-mono">
                  {shortAddr}
                </code>
                <button
                  onClick={copyAddress}
                  className="p-1 hover:bg-zinc-850 rounded border border-zinc-800 transition"
                  title="Copy address"
                >
                  {copySuccess ? (
                    <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Karma & Reputation Badges */}
          <div className="flex flex-wrap gap-4">
            <div className="bg-zinc-950 border border-zinc-850 px-4 py-3 rounded-xl min-w-[100px]">
              <span className="text-xs text-zinc-500 block uppercase tracking-wider font-semibold">Karma</span>
              <span className="text-2xl font-bold text-indigo-400">{karma ?? 0}</span>
            </div>
            <div className="bg-zinc-950 border border-zinc-850 px-4 py-3 rounded-xl min-w-[100px]">
              <span className="text-xs text-zinc-500 block uppercase tracking-wider font-semibold">Reputation</span>
              <span className="text-2xl font-bold text-emerald-400">
                {profile?.reputation_score !== undefined ? `${profile.reputation_score}%` : 'N/A'}
              </span>
            </div>
            {profile?.novice_tier && (
              <div className="flex items-center bg-yellow-500/10 border border-yellow-500/20 px-3 py-1 rounded-full text-xs text-yellow-400 h-fit self-center">
                Novice Tier Restricted
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Stats Column */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-850 rounded-2xl p-6">
            <h2 className="text-lg font-bold mb-4">Performance Stats</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
                <span className="text-sm text-zinc-400">Created Bounties</span>
                <span className="font-semibold text-zinc-200">{profile?.bounties_created ?? 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
                <span className="text-sm text-zinc-400">Claimed Bounties</span>
                <span className="font-semibold text-zinc-200">{profile?.bounties_claimed ?? 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
                <span className="text-sm text-zinc-400">Completed Bounties</span>
                <span className="font-semibold text-zinc-200 text-emerald-400">{profile?.bounties_completed ?? 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
                <span className="text-sm text-zinc-400">Disputes Triggered</span>
                <span className="font-semibold text-zinc-200 text-red-400">{profile?.bounties_disputed ?? 0}</span>
              </div>
              <div className="flex items-center justify-between pb-1">
                <span className="text-sm text-zinc-400">Submissions Rejected</span>
                <span className="font-semibold text-zinc-200 text-orange-400">{profile?.bounties_rejected ?? 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bounties List Column */}
        <div className="lg:col-span-2">
          <div className="bg-zinc-900 border border-zinc-850 rounded-2xl p-6 min-h-[300px]">
            <h2 className="text-lg font-bold mb-4">Your Active & Historical Bounties</h2>

            {loadingBounties ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : bounties.length === 0 ? (
              <div className="text-center py-12 text-zinc-500">
                <svg className="w-12 h-12 text-zinc-600 mx-auto mb-3 fill-none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p>No associated bounties found.</p>
                <Link href="/create" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">
                  Create a new bounty &rarr;
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-zinc-850">
                {bounties.map((b) => {
                  const isUserCreator = b.creator === address;
                  return (
                    <div key={b.bounty_id} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <Link href={`/bounties/${b.bounty_id}`} className="font-semibold text-zinc-100 hover:text-indigo-400 transition">
                            {b.description.length > 60 ? `${b.description.slice(0, 60)}...` : b.description}
                          </Link>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            b.status === 'open' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            b.status === 'claimed' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                            b.status === 'submitted' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                            'bg-zinc-800 text-zinc-400 border border-zinc-700'
                          }`}>
                            {b.status.toUpperCase()}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                          <span>Amount: <b className="text-zinc-300">{(b.amount / 1_000_000).toLocaleString()} ALGO</b></span>
                          <span>•</span>
                          <span>Role: <b className="text-zinc-300">{isUserCreator ? 'Creator' : 'Worker'}</b></span>
                        </div>
                      </div>
                      <Link
                        href={`/bounties/${b.bounty_id}`}
                        className="text-zinc-400 hover:text-zinc-200 border border-zinc-800 hover:border-zinc-700 px-3 py-1.5 rounded-lg text-xs transition shrink-0"
                      >
                        View Details
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
