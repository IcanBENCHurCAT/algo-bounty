'use client';

import { useWallet } from '@/hooks/useWallet';

interface WalletButtonProps {
  variant?: 'default' | 'compact';
  className?: string;
  onConnect?: () => void;
}

export default function WalletConnect({
  variant = 'default',
  className = '',
  onConnect,
}: WalletButtonProps) {
  const { address, connected, loading, error, connect, disconnect } = useWallet();

  const handleConnect = () => {
    if (connected) {
      disconnect();
    } else {
      connect();
    }
  };

  if (error && !connected) {
    return (
      <div className="relative">
        <button
          onClick={handleConnect}
          className={`flex items-center gap-2 rounded-lg bg-transparent border border-amber-500/50 px-3 py-2 text-sm text-amber-400 hover:bg-amber-500/10 transition-colors ${className}`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          {variant === 'compact' ? 'Wallet Error' : error}
        </button>
      </div>
    );
  }

  if (connected && address) {
    const shortAddr = `${address.slice(0, 6)}...${address.slice(-4)}`;
    return (
      <div className="flex items-center gap-2">
        <span className="hidden sm:inline text-sm text-gray-400">{shortAddr}</span>
        <button
          onClick={disconnect}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-sm text-amber-400 hover:bg-amber-500/20 transition-colors"
          title="Disconnect wallet"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className={variant === 'compact' ? 'hidden sm:inline' : ''}>
            Disconnect
          </span>
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={handleConnect}
      disabled={loading}
      className={`flex items-center gap-2 rounded-lg bg-blue-600/20 border border-blue-500/40 px-3 py-2 text-sm text-blue-400 hover:bg-blue-600/30 hover:border-blue-400/60 transition-colors disabled:opacity-50 ${className}`}
    >
      {loading ? (
        <>
          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Connecting...
        </>
      ) : (
        <>
          <WalletIcon />
          <span className={variant === 'compact' ? 'hidden sm:inline' : ''}>
            Connect Wallet
          </span>
        </>
      )}
    </button>
  );
}

function WalletIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="6" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 6V4a2 2 0 012-2h8a2 2 0 012 2v2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="13" r="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
