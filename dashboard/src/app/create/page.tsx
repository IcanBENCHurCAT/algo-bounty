'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useWallet } from '@/hooks/useWallet';
import { useToast } from '@/components/Toast';
import { createBounty } from '@/lib/api';

type Step = 'details' | 'requirements' | 'payment' | 'deploying';

export default function CreateBountyPage() {
  const router = useRouter();
  const toast = useToast();
  const { connected, jwt, profile } = useWallet();

  const [step, setStep] = useState<Step>('details');
  const [loading, setLoading] = useState(false);
  const [deployStep, setDeployStep] = useState(0);

  // Form State
  const [description, setDescription] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [amount, setAmount] = useState('');
  const [minKarma, setMinKarma] = useState('0');
  const [hitm, setHitm] = useState(false);
  const [tags, setTags] = useState('');

  // Validation
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateDetails = () => {
    const newErrors: Record<string, string> = {};
    if (description.length < 10) newErrors.description = 'Description must be at least 10 characters';
    if (repoUrl && !repoUrl.includes('github.com')) newErrors.repoUrl = 'Only GitHub repositories are supported currently';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePayment = () => {
    const newErrors: Record<string, string> = {};
    const val = parseFloat(amount);
    if (isNaN(val) || val <= 0) newErrors.amount = 'Amount must be greater than 0';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 'details' && validateDetails()) setStep('requirements');
    else if (step === 'requirements') setStep('payment');
  };

  const handleBack = () => {
    if (step === 'requirements') setStep('details');
    else if (step === 'payment') setStep('requirements');
  };

  const handleSubmit = async () => {
    if (!validatePayment()) return;
    if (!connected || !jwt) {
      toast.error('Connect your wallet first');
      return;
    }

    setStep('deploying');
    setLoading(true);

    try {
      // Step 1: Initialize
      setDeployStep(1);
      await new Promise(r => setTimeout(r, 1000));

      // Step 2: Sign
      setDeployStep(2);
      // In production, this would call createBounty which might return a transaction to sign
      await createBounty({
        description,
        amount: parseFloat(amount) * 1_000_000,
        repo_url: repoUrl || undefined,
        karma_requirement: parseInt(minKarma),
        hitm,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      }, jwt);

      // Step 3: Deploy
      setDeployStep(3);
      await new Promise(r => setTimeout(r, 1500));

      // Step 4: Indexing
      setDeployStep(4);
      await new Promise(r => setTimeout(r, 1000));

      toast.success('Bounty created and deployed successfully!');
      router.push('/');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create bounty';
      toast.error(msg);
      setStep('payment');
    } finally {
      setLoading(false);
    }
  };

  if (!connected) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Create a New Bounty</h1>
        <p className="text-gray-400 mb-8">You need to connect your wallet to create a bounty on the Algorand blockchain.</p>
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
            Please use the &quot;Connect Wallet&quot; button in the header.
        </div>
      </div>
    );
  }

  const deploySteps = [
    'Initializing bounty data...',
    'Requesting wallet signature...',
    'Deploying smart contract to Algorand...',
    'Finalizing and indexing...',
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Progress */}
      {step !== 'deploying' && (
        <div className="flex items-center justify-between mb-8">
          {(['details', 'requirements', 'payment'] as const).map((s, i) => (
            <div key={s} className="flex items-center flex-1 last:flex-none">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                step === s ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' :
                i < ['details', 'requirements', 'payment'].indexOf(step) ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                'bg-gray-800 text-gray-500 border border-gray-700'
              }`}>
                {i < ['details', 'requirements', 'payment'].indexOf(step) ? '✓' : i + 1}
              </div>
              {i < 2 && (
                <div className={`h-0.5 flex-1 mx-2 ${
                  i < ['details', 'requirements', 'payment'].indexOf(step) ? 'bg-emerald-500/30' : 'bg-gray-800'
                }`} />
              )}
            </div>
          ))}
        </div>
      )}

      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 sm:p-8">
        {step === 'details' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-xl font-bold mb-1">Bounty Details</h1>
              <p className="text-sm text-gray-500">Describe what needs to be done.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Description *</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="E.g. Fix bug in authentication flow..."
                  className={`w-full bg-gray-800/50 border ${errors.description ? 'border-red-500/50' : 'border-gray-700'} rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none min-h-[120px]`}
                />
                {errors.description && <p className="text-xs text-red-400 mt-1">{errors.description}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">GitHub Repository URL (optional)</label>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/org/repo"
                  className={`w-full bg-gray-800/50 border ${errors.repoUrl ? 'border-red-500/50' : 'border-gray-700'} rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none`}
                />
                {errors.repoUrl && <p className="text-xs text-red-400 mt-1">{errors.repoUrl}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Tags (comma separated)</label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="react, typescript, algorand"
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <button onClick={handleNext} className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 font-medium transition-colors">
              Continue to Requirements
            </button>
          </div>
        )}

        {step === 'requirements' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-xl font-bold mb-1">Worker Requirements</h1>
              <p className="text-sm text-gray-500">Filter who can claim this bounty.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Minimum Karma Requirement</label>
                <input
                  type="number"
                  value={minKarma}
                  onChange={(e) => setMinKarma(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
                />
                <p className="text-xs text-gray-600 mt-1.5">Your current karma: {profile?.karma || 0}</p>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-800/30 border border-gray-700 rounded-xl">
                <div>
                  <label className="block text-sm font-medium text-gray-200">Human-in-the-Middle (HITM)</label>
                  <p className="text-xs text-gray-500">Manual review required before payout</p>
                </div>
                <button
                  onClick={() => setHitm(!hitm)}
                  className={`w-12 h-6 rounded-full transition-colors relative ${hitm ? 'bg-blue-600' : 'bg-gray-700'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${hitm ? 'left-7' : 'left-1'}`} />
                </button>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleBack} className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl py-3 font-medium transition-colors">
                Back
              </button>
              <button onClick={handleNext} className="flex-[2] bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 font-medium transition-colors">
                Continue to Payment
              </button>
            </div>
          </div>
        )}

        {step === 'payment' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-xl font-bold mb-1">Payment & Payout</h1>
              <p className="text-sm text-gray-500">Set the bounty amount and fund the escrow.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Bounty Amount (ALGO) *</label>
                <div className="relative">
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="10.0"
                    className={`w-full bg-gray-800/50 border ${errors.amount ? 'border-red-500/50' : 'border-gray-700'} rounded-xl px-4 py-3 text-lg font-bold text-gray-100 placeholder-gray-700 focus:border-blue-500 focus:outline-none`}
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 font-bold">ALGO</span>
                </div>
                {errors.amount && <p className="text-xs text-red-400 mt-1">{errors.amount}</p>}
              </div>

              <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-xs text-gray-400 leading-relaxed">
                <p>Funds will be locked in an on-chain escrow contract. They can only be released upon work approval or refunded after the deadline if unclaimed.</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleBack} className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl py-3 font-medium transition-colors">
                Back
              </button>
              <button onClick={handleSubmit} className="flex-[2] bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl py-3 font-bold shadow-lg shadow-blue-600/20 transition-all">
                Deploy & Fund Bounty
              </button>
            </div>
          </div>
        )}

        {step === 'deploying' && (
          <div className="py-8 text-center space-y-8">
            <div className="relative w-20 h-20 mx-auto">
              <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full" />
              <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-blue-500 font-bold">{Math.min(100, deployStep * 25)}%</span>
              </div>
            </div>

            <div>
              <h2 className="text-xl font-bold mb-2">Deploying to Blockchain</h2>
              <p className="text-gray-500 text-sm">Please do not close this window.</p>
            </div>

            <div className="space-y-3 max-w-xs mx-auto">
              {deploySteps.map((s, i) => (
                <div key={i} className={`flex items-center gap-3 text-left transition-opacity duration-500 ${deployStep > i ? 'opacity-100' : deployStep === i ? 'opacity-100 animate-pulse' : 'opacity-30'}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${deployStep > i ? 'bg-emerald-500 text-white' : 'bg-gray-800 text-gray-500'}`}>
                    {deployStep > i ? '✓' : i + 1}
                  </div>
                  <span className={`text-sm ${deployStep === i ? 'text-blue-400 font-medium' : 'text-gray-400'}`}>{s}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
