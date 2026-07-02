'use client';

import { useState, useMemo } from 'react';
import BountyCard from '@/components/BountyCard';
import { getBounties, type Bounty } from '@/lib/api';

type StatusFilter = 'open' | 'claimed' | 'submitted' | 'approved' | 'disputed' | 'refunded' | 'closed' | 'all';
type HitmFilter = 'any' | 'true' | 'false';

export default function MarketplacePage() {
  const [bounties, setBounties] = useState<Bounty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  // Filters
  const [status, setStatus] = useState<StatusFilter>('all');
  const [hitm, setHitm] = useState<HitmFilter>('any');
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [repo, setRepo] = useState('');
  const [minKarma, setMinKarma] = useState('');
  const [sortBy, setSortBy] = useState('created_at');

  const loadBounties = useMemo(
    () => async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, unknown> = { page: p, limit: 20 };
        if (status !== 'all') params.status = status;
        if (hitm !== 'any') params.hitm = hitm;
        if (minAmount) params.min_amount = Number(minAmount) * 1_000_000; // convert ALGO to microALGO
        if (maxAmount) params.max_amount = Number(maxAmount) * 1_000_000;
        if (repo) params.repo = repo;
        if (minKarma) params.min_karma = Number(minKarma);
        if (sortBy) params.sort = sortBy;

        const res = await getBounties(params);
        if (p === 1) setBounties(res.bounties);
        else setBounties((prev) => [...prev, ...res.bounties]);
        setHasMore(res.has_more);
        setTotal(res.total);
        setPage(p);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load bounties');
      } finally {
        setLoading(false);
      }
    },
    [status, hitm, minAmount, maxAmount, repo, minKarma, sortBy],
  );

  const handleSearch = () => {
    loadBounties(1);
  };

  const handleReset = () => {
    setStatus('all');
    setHitm('any');
    setMinAmount('');
    setMaxAmount('');
    setRepo('');
    setMinKarma('');
    setSortBy('created_at');
    loadBounties(1);
  };

  // Load on mount
  useState(() => {
    loadBounties(1);
  });

  const statusOptions: StatusFilter[] = ['all', 'open', 'claimed', 'submitted', 'approved', 'disputed', 'refunded', 'closed'];
  const hitmOptions: HitmFilter[] = ['any', 'true', 'false'];
  const sortOptions = [
    { value: 'created_at', label: 'Newest' },
    { value: 'amount', label: 'Amount' },
    { value: 'karma_required', label: 'Karma' },
    { value: 'deadline', label: 'Deadline' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold mb-1">
          <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            AlgoBounty
          </span>{' '}
          Marketplace
        </h1>
        <p className="text-gray-400 text-sm">
          {total > 0 ? `${total.toLocaleString()} bounties available` : 'Loading bounties...'}
        </p>
      </div>

      {/* Filters */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Status */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as StatusFilter)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
            >
              {statusOptions.map((s) => (
                <option key={s} value={s}>{s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
          </div>

          {/* HITM */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">HITM</label>
            <select
              value={hitm}
              onChange={(e) => setHitm(e.target.value as HitmFilter)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
            >
              {hitmOptions.map((h) => (
                <option key={h} value={h}>{h === 'any' ? 'Any' : h === 'true' ? 'With HITM' : 'No HITM'}</option>
              ))}
            </select>
          </div>

          {/* Sort */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Sort</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
            >
              {sortOptions.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Min amount */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Min (ALGO)</label>
            <input
              type="number"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
              placeholder="0"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Max amount */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Max (ALGO)</label>
            <input
              type="number"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              placeholder="∞"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Second row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Repo (partial)</label>
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="github.com/..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Min Karma</label>
            <input
              type="number"
              value={minKarma}
              onChange={(e) => setMinKarma(e.target.value)}
              placeholder="0"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={handleSearch}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              Search
            </button>
            <button
              onClick={handleReset}
              className="bg-gray-800 hover:bg-gray-700 text-gray-400 rounded-lg px-4 py-2 text-sm transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Bounty grid */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && bounties.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-gray-900/80 border border-gray-800 rounded-xl p-5 animate-pulse">
              <div className="h-4 w-16 bg-gray-800 rounded mb-3" />
              <div className="h-5 w-full bg-gray-800 rounded mb-2" />
              <div className="h-5 w-2/3 bg-gray-800 rounded mb-3" />
              <div className="h-6 w-24 bg-gray-800 rounded mb-3" />
              <div className="h-3 w-32 bg-gray-800 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <>
          {bounties.length === 0 ? (
            <div className="text-center py-16">
              <svg className="w-16 h-16 mx-auto text-gray-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-500 text-lg">No bounties found</p>
              <p className="text-gray-600 text-sm mt-1">Try adjusting your filters</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {bounties.map((bounty) => (
                <BountyCard key={bounty.bounty_id} bounty={bounty} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {hasMore && (
            <div className="mt-8 text-center">
              <button
                onClick={() => loadBounties(page + 1)}
                className="bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg px-6 py-2.5 text-sm font-medium transition-colors"
              >
                Load More ({bounties.length}+)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
