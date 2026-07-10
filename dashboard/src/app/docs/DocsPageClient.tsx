'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState, useCallback } from 'react';
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

  const scrollToSection = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const offset = 80;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
    setSidebarOpen(false);
  }, []);

  return (
    <div className="flex flex-1 max-w-[1400px] w-full mx-auto">
      {/* Sidebar Overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 sm:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-16 left-0 bottom-0 z-30 w-64 bg-[#0a0a0a] border-r border-gray-800/60 overflow-y-auto transition-transform duration-200 sm:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <DocsNav tocItems={tocItems} />
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 sm:ml-64">
        <div className="py-6 px-4 sm:px-8">
          <div className="max-w-4xl">
            {/* Title */}
            <div className="mb-8">
              <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent leading-tight">
                AlgoBounty
              </h1>
              <p className="text-lg text-gray-400 mt-2">
                Decentralized Agent-to-Agent Bounty Marketplace
              </p>
              <div className="w-20 h-0.5 bg-gradient-to-r from-blue-500 to-cyan-500 mt-4 rounded" />
            </div>

            {/* Markdown Content */}
            <article className="prose prose-invert max-w-none prose-headings:text-white prose-a:text-blue-400 prose-a:no-underline hover:prose-a:text-blue-300 prose-code:text-cyan-300 prose-code:bg-gray-800/80 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-950 prose-pre:border prose-pre:border-gray-800/60 prose-pre:rounded-lg prose-blockquote:border-l-blue-500/60 prose-blockquote:bg-blue-500/5 prose-blockquote:text-gray-400 prose-th:bg-gray-800/60 prose-th:border prose-th:border-gray-700/60 prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-800/60 prose-td:px-4 prose-td:py-2 prose-td:text-gray-300 prose-img:rounded-lg prose-hr:border-gray-800/60 prose-h3:text-lg prose-h3:font-semibold prose-h3:text-gray-200">
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
                        className="text-2xl font-bold text-white mt-12 mb-4 pb-2 border-b border-gray-800/60 scroll-mt-20 group"
                        {...props}
                      >
                        <a
                          href={`#${id}`}
                          className="no-underline hover:text-blue-400 transition-colors"
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
                        className="text-lg font-semibold text-gray-200 mt-8 mb-3 scroll-mt-20 group"
                        {...props}
                      >
                        <a
                          href={`#${id}`}
                          className="no-underline hover:text-blue-400 transition-colors"
                        >
                          {children}
                          <span className="ml-2 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity text-sm">
                            #
                          </span>
                        </a>
                      </h3>
                    );
                  },
                  code: ({ node, children, className, ...props }) => {
                    const inline = !className;
                    if (inline) {
                      return (
                        <code
                          className="bg-gray-800/80 text-cyan-300 px-1.5 py-0.5 rounded text-sm font-mono"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }
                    return <code className={className} {...props}>{children}</code>;
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
