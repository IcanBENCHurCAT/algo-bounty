'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getBounty, approveWork, rejectWork, submitWork, claimBounty, getClaimTxn, getApproveTxn, getStoredToken, type Bounty } from '@/lib/api';
import { useWallet } from '@/hooks/useWallet';
import { useToast } from '@/components/Toast';
import { useEvents } from '@/hooks/useEvents';

export default function BountyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const { connected, address, jwt, signTransaction } = useWallet();

  const [bounty, setBounty] = useState<Bounty | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState('');
  const [prLoading, setPrLoading] = useState(false);
  const [approveLoading, setApproveLoading] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);

  const bountyId = typeof params.bounty_id === 'string' ? params.bounty_id : String(params.bounty_id);

  const loadBounty = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getBounty(bountyId);
      setBounty(data);
    } catch {
      setError('Bounty not found');
    } finally {
      setLoading(false);
    }
  }, [bountyId]);

  useEffect(() => {
    const timeout = setTimeout(loadBounty, 0);
    return () => clearTimeout(timeout);
  }, [loadBounty]);

  // Real-time updates for this specific bounty
  useEvents(useCallback((event) => {
    if ((event.data as Record<string, unknown>)?.bounty_id === bountyId) {
      if (event.event_type === 'bounty.claimed') toast.info('Bounty has been claimed');
      if (event.event_type === 'bounty.submitted') toast.info('New work submitted');
      if (event.event_type === 'bounty.approved') toast.success('Bounty approved!');
    }
  }, [bountyId, loadBounty, toast]));

  const shortAddr = address ? `${address.slice(0, 6)}...${address.slice(-4)}` : '';
  const shortCreator = bounty ? `${bounty.creator.slice(0, 6)}...${bounty.creator.slice(-4)}` : '';
  const isCreator = address ? bounty?.creator === address : false;
  const isWorker = address ? bounty?.worker === address : false;

  const amountAlgo = bounty ? (bounty.amount / 1_000_000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : '0';

  const handleClaim = async () => {
    if (!connected || !jwt) {
      toast.error('Connect your wallet first');
      return;
    }
    setActionLoading('claim');
    try {
      toast.warning('Generating claim transaction...');
      const { unsigned_txn } = await getClaimTxn(bountyId, jwt);
      
      toast.info('Sign the escrow transaction in your wallet...');
      const signed_txn = await signTransaction(unsigned_txn);
      
      toast.warning('Submitting claim to network...');
      await claimBounty(bountyId, { signed_txn }, jwt);
      toast.success('Bounty claimed successfully!');
      await loadBounty();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Claim failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSubmit = async () => {
    if (!connected || !jwt) {
      toast.error('Connect your wallet first');
      return;
    }
    if (!prUrl.trim()) {
      toast.error('Please enter a PR URL');
      return;
    }
    setPrLoading(true);
    try {
      await submitWork(bountyId, { pr_url: prUrl }, jwt);
      toast.success('Work submitted successfully!');
      setPrUrl('');
      await loadBounty();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Submit failed');
    } finally {
      setPrLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!connected || !jwt) {
      toast.error('Connect your wallet first');
      return;
    }
    setApproveLoading(true);
    try {
      toast.warning('Generating approval transaction...');
      const { unsigned_txn } = await getApproveTxn(bountyId, jwt);
      
      toast.info('Sign the payout transaction in your wallet...');
      const signed_txn = await signTransaction(unsigned_txn);
      
      toast.warning('Releasing funds on-chain...');
      await approveWork(bountyId, { signed_txn }, jwt);
      toast.success('Bounty approved! Funds released.');
      await loadBounty();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Approve failed');
    } finally {
      setApproveLoading(false);
    }
  };

  const handleReject = async () => {
    if (!connected || !jwt) {
      toast.error('Connect your wallet first');
      return;
    }
    setRejectLoading(true);
    try {
      await rejectWork(bountyId, jwt, { signed_txn: '' });
      toast.warning('Bounty rejected.');
      await loadBounty();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Reject failed');
    } finally {
      setRejectLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-6 w-32 bg-gray-800 rounded" />
          <div className="h-8 w-full bg-gray-800 rounded" />
          <div className="h-4 w-2/3 bg-gray-800 rounded" />
          <div className="h-40 w-full bg-gray-800 rounded-xl" />
          <div className="h-12 w-40 bg-gray-800 rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !bounty) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <p className="text-red-400 mb-3">{error || 'Bounty not found'}</p>
          <button onClick={() => router.push('/')} className="text-blue-400 hover:text-blue-300 text-sm">
            ← Back to Marketplace
          </button>
        </div>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    open: 'bg-green-500/15 text-green-400 border-green-500/30',
    claimed: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    submitted: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    approved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    disputed: 'bg-red-500/15 text-red-400 border-red-500/30',
    refunded: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
    closed: 'bg-gray-500/15 text-gray-500 border-gray-600/30',
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      {/* Back */}
      <button onClick={() => router.push('/')} className="flex items-center gap-1.5 text-gray-400 hover:text-gray-200 text-sm mb-4 transition-colors">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        Back to Marketplace
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusColors[bounty.status] || statusColors.open}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${bounty.status === 'open' ? 'bg-green-400' : bounty.status === 'claimed' || bounty.status === 'submitted' ? 'bg-blue-400' : bounty.status === 'approved' ? 'bg-emerald-400' : bounty.status === 'disputed' ? 'bg-red-400' : 'bg-gray-400'}`} />
              {bounty.status.charAt(0).toUpperCase() + bounty.status.slice(1)}
            </span>
            <span className="text-xs text-gray-500 font-mono">{bounty.bounty_id}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100">{bounty.description}</h1>
        </div>
        <div className="text-left sm:text-right">
          <div className="text-2xl font-bold text-cyan-400">{amountAlgo} <span className="text-sm text-gray-400 font-normal">ALGO</span></div>
          {bounty.hitm && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-orange-500/15 text-orange-400 border border-orange-500/30 mt-1">HITM Required</span>
          )}
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-3">
          <div className="text-xs text-gray-500 mb-1">Creator</div>
          <div className="text-sm font-mono text-gray-300">{shortCreator}</div>
        </div>
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-3">
          <div className="text-xs text-gray-500 mb-1">Created</div>
          <div className="text-sm text-gray-300">{new Date(bounty.created_at).toLocaleDateString()}</div>
        </div>
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-3">
          <div className="text-xs text-gray-500 mb-1">Karma Required</div>
          <div className="text-sm text-gray-300">{bounty.karma_requirement}</div>
        </div>
        {bounty.repo_url && (
          <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-3">
            <div className="text-xs text-gray-500 mb-1">Repository</div>
            <div className="text-sm text-gray-300 truncate">{new URL(bounty.repo_url).hostname}</div>
          </div>
        )}
      </div>

      {/* Description */}
      {bounty.description && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-2">Description</h2>
          <p className="text-sm text-gray-400 whitespace-pre-wrap">{bounty.description}</p>
        </div>
      )}

      {/* Repo */}
      {bounty.repo_url && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-2">Repository</h2>
          <a href={bounty.repo_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 text-sm break-all">{bounty.repo_url}</a>
          {bounty.repo_labels?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {bounty.repo_labels.map((l) => (<span key={l} className="px-2 py-0.5 rounded bg-gray-800 text-gray-400 text-xs">{l}</span>))}
            </div>
          )}
        </div>
      )}

      {/* Tags */}
      {bounty.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {bounty.tags.map((tag) => (
            <span key={tag} className="px-2.5 py-1 rounded-full bg-gray-800/60 border border-gray-700 text-gray-400 text-xs">{tag}</span>
          ))}
        </div>
      )}

      {/* Escrow */}
      {bounty.app_id && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-2">On-Chain Status</h2>
          <div className="text-xs text-gray-500">App ID: <span className="text-gray-300 font-mono">#{bounty.app_id}</span></div>
        </div>
      )}

      {/* Worker */}
      {(bounty.status === 'claimed' || bounty.status === 'submitted') && bounty.worker && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-2">Worker</h2>
          <div className="text-sm font-mono text-gray-300">
            {bounty.worker === address ? <span className="text-blue-400">You (worker)</span> : `${bounty.worker.slice(0, 8)}...${bounty.worker.slice(-4)}`}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-3">
        {bounty.status === 'open' && !isCreator && (
          <button onClick={handleClaim} disabled={!connected || actionLoading === 'claim'} className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-8 py-3 font-medium transition-all flex items-center justify-center gap-2">
            {actionLoading === 'claim' ? (
              <>
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                Claiming...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                Claim Bounty
              </>
            )}
          </button>
        )}

        {bounty.status === 'claimed' && isWorker && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input type="url" value={prUrl} onChange={(e) => setPrUrl(e.target.value)} placeholder="https://github.com/org/repo/pull/42" className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none" />
              <button onClick={handleSubmit} disabled={!prUrl.trim() || prLoading} className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 py-3 font-medium transition-colors whitespace-nowrap">
                {prLoading ? 'Submitting...' : 'Submit Work'}
              </button>
            </div>
            <p className="text-xs text-gray-600">Enter the PR URL for your completed work</p>
          </div>
        )}

        {bounty.status === 'submitted' && isCreator && (
          <div className="flex flex-col sm:flex-row gap-3">
            <button onClick={handleApprove} disabled={approveLoading} className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 py-3 font-medium transition-colors flex items-center justify-center gap-2">
              {approveLoading ? 'Approving...' : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                  Approve & Payout
                </>
              )}
            </button>
            <button onClick={handleReject} disabled={rejectLoading} className="flex-1 bg-red-600/80 hover:bg-red-500/80 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 py-3 font-medium transition-colors flex items-center justify-center gap-2">
              {rejectLoading ? 'Rejecting...' : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  Reject
                </>
              )}
            </button>
          </div>
        )}

        {bounty.status === 'disputed' && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-amber-400 text-sm text-center">
            ⚠️ This bounty is in dispute. Mediation will be handled by a trusted mediator.
          </div>
        )}

        {['approved', 'closed', 'refunded'].includes(bounty.status) && (
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 text-gray-500 text-sm text-center">
            This bounty is {bounty.status === 'approved' ? 'completed with payout' : bounty.status === 'refunded' ? 'refunded' : 'closed'}.
          </div>
        )}

        {!connected && bounty.status === 'open' && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-blue-400 text-sm text-center">
            Connect your Pera Wallet to claim this bounty or create new ones.
          </div>
        )}
      </div>
    </div>
  );
}
