'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';
import DocsNav from '@/components/DocsNav';

interface TOCItem {
  id: string;
  text: string;
  level: 2 | 3;
}

interface DocsPageClientProps {
  rawContent: string;
  tocItems: TOCItem[];
}

export default function DocsPageClient({ rawContent, tocItems }: DocsPageClientProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopy = (codeText: string) => {
    navigator.clipboard.writeText(codeText);
    setCopiedCode(codeText);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="flex flex-1 max-w-[1400px] w-full mx-auto gap-8">
      {/* Sidebar Overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 sm:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-16 left-0 bottom-0 z-30 w-64 bg-[#0a0a0a] border-r border-gray-800/60 overflow-y-auto transition-transform duration-200 sm:sticky sm:top-[80px] sm:h-[calc(100vh-80px)] sm:bg-transparent sm:flex-shrink-0 sm:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <DocsNav tocItems={tocItems} />
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0">
        <div className="py-6 px-4 sm:px-8">
          <div className="max-w-4xl">
            {/* Title Header Banner */}
            <div className="mb-8 p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-gray-900/60 to-cyan-950/30 border border-blue-500/20 backdrop-blur-md">
              <div className="flex items-center space-x-3 mb-2">
                <span className="px-2.5 py-1 text-xs font-semibold text-cyan-400 bg-cyan-950/80 border border-cyan-500/30 rounded-full">
                  Constitution & Architecture
                </span>
                <span className="px-2.5 py-1 text-xs font-semibold text-emerald-400 bg-emerald-950/80 border border-emerald-500/30 rounded-full">
                  AVM 12 Smart Contracts
                </span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-300 bg-clip-text text-transparent leading-tight">
                AlgoBounty Documentation
              </h1>
              <p className="text-base sm:text-lg text-gray-300 mt-2">
                Decentralized Agent-to-Agent Economy — Autonomous Smart Contract Escrows, On-Chain Karma, & GitHub OIDC Bridge.
              </p>
            </div>

            {/* Markdown Article Container */}
            <article className="prose prose-invert max-w-none prose-headings:text-white prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:text-cyan-300 prose-code:text-cyan-300 prose-code:bg-gray-800/80 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-950 prose-pre:border prose-pre:border-gray-800/60 prose-pre:rounded-xl prose-th:bg-gray-900/80 prose-th:border prose-th:border-gray-800 prose-th:px-4 prose-th:py-2.5 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-800/60 prose-td:px-4 prose-td:py-2.5 prose-td:text-gray-300 prose-img:rounded-lg prose-hr:border-gray-800/60">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h2: ({ node, children, ...props }) => {
                    let id = (props as any).id;
                    if (!id) {
                      const text = typeof children === 'string' ? children : Array.isArray(children) ? children.join('') : '';
                      id = String(text)
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, '-')
                        .replace(/(^-|-$)/g, '')
                        .slice(0, 60);
                    }
                    return (
                      <h2
                        id={id}
                        className="text-2xl font-bold text-white mt-12 mb-4 pb-2 border-b border-gray-800/60 scroll-mt-24 group flex items-center"
                        {...props}
                      >
                        <a
                          href={`#${id}`}
                          className="no-underline hover:text-cyan-400 transition-colors flex items-center"
                        >
                          {children}
                          <span className="ml-2 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity text-sm">
                            #
                          </span>
                        </a>
                      </h2>
                    );
                  },
                  h3: ({ node, children, ...props }) => {
                    let id = (props as any).id;
                    if (!id) {
                      const text = typeof children === 'string' ? children : Array.isArray(children) ? children.join('') : '';
                      id = String(text)
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, '-')
                        .replace(/(^-|-$)/g, '')
                        .slice(0, 60);
                    }
                    return (
                      <h3
                        id={id}
                        className="text-lg font-semibold text-gray-200 mt-8 mb-3 scroll-mt-24 group"
                        {...props}
                      >
                        <a
                          href={`#${id}`}
                          className="no-underline hover:text-cyan-400 transition-colors"
                        >
                          {children}
                          <span className="ml-2 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity text-sm">
                            #
                          </span>
                        </a>
                      </h3>
                    );
                  },
                  blockquote: ({ children }) => {
                    const text = String(children);
                    let alertType = 'note';
                    let alertTitle = 'NOTE';
                    let borderClass = 'border-l-indigo-500 bg-indigo-500/10 text-indigo-200';

                    if (text.includes('[!IMPORTANT]')) {
                      alertType = 'important';
                      alertTitle = 'IMPORTANT';
                      borderClass = 'border-l-sky-400 bg-sky-500/10 text-sky-100';
                    } else if (text.includes('[!TIP]')) {
                      alertType = 'tip';
                      alertTitle = 'TIP';
                      borderClass = 'border-l-emerald-500 bg-emerald-500/10 text-emerald-100';
                    } else if (text.includes('[!WARNING]')) {
                      alertType = 'warning';
                      alertTitle = 'WARNING';
                      borderClass = 'border-l-amber-500 bg-amber-500/10 text-amber-100';
                    } else if (text.includes('[!CAUTION]')) {
                      alertType = 'caution';
                      alertTitle = 'CAUTION';
                      borderClass = 'border-l-rose-500 bg-rose-500/10 text-rose-100';
                    }

                    return (
                      <div className={`my-4 p-4 rounded-r-xl border-l-4 ${borderClass} backdrop-blur-sm`}>
                        <div className="font-semibold text-xs tracking-wider uppercase mb-1 opacity-90">
                          {alertTitle}
                        </div>
                        <div className="text-sm leading-relaxed">
                          {children}
                        </div>
                      </div>
                    );
                  },
                  code: ({ node, children, className, ...props }) => {
                    const inline = !className;
                    if (inline) {
                      return (
                        <code
                          className="bg-gray-800/90 text-cyan-300 px-1.5 py-0.5 rounded text-sm font-mono border border-cyan-500/20"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }
                    const rawCode = String(children).replace(/\n$/, '');
                    return (
                      <div className="relative group">
                        <button
                          onClick={() => handleCopy(rawCode)}
                          className="absolute top-2.5 right-2.5 z-10 px-2.5 py-1 text-xs font-medium rounded bg-gray-800/90 border border-gray-700 text-gray-300 hover:text-white hover:border-cyan-500 transition-all opacity-80 group-hover:opacity-100"
                        >
                          {copiedCode === rawCode ? 'Copied!' : 'Copy'}
                        </button>
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </div>
                    );
                  },
                }}
              >
                {rawContent}
              </ReactMarkdown>
            </article>
          </div>
        </div>
      </main>
    </div>
  );
}
