'use client';

import Link from 'next/link';
import type { Bounty } from '@/lib/api';

interface BountyCardProps {
  bounty: Bounty;
  onClick?: () => void;
}

export default function BountyCard({ bounty, onClick }: BountyCardProps) {
  const statusColors: Record<string, string> = {
    open: 'bg-green-500/15 text-green-400 border-green-500/30',
    claimed: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    submitted: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    approved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    disputed: 'bg-red-500/15 text-red-400 border-red-500/30',
    refunded: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
    closed: 'bg-gray-500/15 text-gray-500 border-gray-600/30',
  };

  const amountAlgo = (bounty.amount / 1_000_000).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });

  const daysRemaining = bounty.deadline_rounds_remaining
    ? Math.ceil(bounty.deadline_rounds_remaining / 1440)
    : null;

  const shortCreator = `${bounty.creator.slice(0, 6)}...${bounty.creator.slice(-4)}`;

  const timeAgo = getTimeAgo(bounty.created_at);

  return (
    <Link
      href={`/bounties/${bounty.bounty_id}`}
      onClick={(e) => {
        if (onClick) {
          e.preventDefault();
          onClick();
        }
      }}
      className="group block bg-gray-900/80 border border-gray-800 rounded-xl p-5 hover:border-blue-500/40 hover:bg-gray-800/60 transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/5"
    >
      {/* Header: status + bounty_id */}
      <div className="flex items-center justify-between mb-3">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
            statusColors[bounty.status] || statusColors.open
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              bounty.status === 'open'
                ? 'bg-green-400'
                : bounty.status === 'claimed' || bounty.status === 'submitted'
                  ? 'bg-blue-400'
                  : bounty.status === 'approved'
                    ? 'bg-emerald-400'
                    : bounty.status === 'disputed'
                      ? 'bg-red-400'
                      : 'bg-gray-400'
            }`}
          />
          {capitalize(bounty.status)}
        </span>
        <span className="text-xs text-gray-500 font-mono">{bounty.bounty_id}</span>
      </div>

      {/* Description */}
      <h3 className="text-sm font-semibold text-gray-100 mb-2 line-clamp-2 group-hover:text-blue-400 transition-colors">
        {bounty.description}
      </h3>

      {/* Amount + Meta row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-cyan-400">
            {amountAlgo} <span className="text-xs text-gray-400 font-normal">ALGO</span>
          </span>
          {bounty.hitm && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-orange-500/15 text-orange-400 border border-orange-500/30"
              title="Human-in-the-Loop review required"
            >
              HITM
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">{timeAgo}</span>
      </div>

      {/* Bottom row: repo, karma, tags */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
        {bounty.repo_url && (
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
              />
            </svg>
            <span className="truncate max-w-[120px]">
              {new URL(bounty.repo_url).hostname}
            </span>
          </span>
        )}
        {bounty.karma_requirement > 0 && (
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              />
            </svg>
            {bounty.karma_requirement} karma
          </span>
        )}
        {daysRemaining !== null && (
          <span>{daysRemaining}d remaining</span>
        )}
        {bounty.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 ml-auto">
            {bounty.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function getTimeAgo(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
