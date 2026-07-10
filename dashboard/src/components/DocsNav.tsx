'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useState, useEffect } from 'react';

interface TOCItem {
  id: string;
  text: string;
  level: 2 | 3;
}

interface DocsNavProps {
  tocItems: TOCItem[];
  className?: string;
}

export default function DocsNav({ tocItems, className = '' }: DocsNavProps) {
  const pathname = usePathname();
  const [scrollId, setScrollId] = useState<string | null>(null);

  const scrollToSection = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const offset = 80;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  }, []);

  // Track which heading is currently in view using IntersectionObserver
  useEffect(() => {
    const headings = tocItems
      .filter((item) => item.level >= 2)
      .map((item) => item.id);

    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setScrollId(entry.target.id);
          }
        });
      },
      { rootMargin: '-80px 0px -80% 0px', threshold: 1.0 }
    );

    const els: HTMLElement[] = [];
    headings.forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.id = id; // ensure id matches
        els.push(el);
      }
    });

    els.forEach((el) => observer.observe(el));

    return () => {
      els.forEach((el) => observer.unobserve(el));
    };
  }, [tocItems]);

  return (
    <nav className={className}>
      <div className="p-4 sticky top-0 bg-[#0a0a0a] pb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
          Table of Contents
        </h3>
        <div className="border-t border-gray-800/60 my-2" />
      </div>
      <ul className="px-3 pb-4">
        {tocItems.map((item) => {
          const isActive =
            pathname === '/docs' && scrollId === item.id;
          return (
            <li key={item.id}>
              <button
                onClick={() => scrollToSection(item.id)}
                className={`w-full text-left block py-1.5 px-2 rounded-md text-sm transition-colors truncate ${
                  item.level === 3 ? 'pl-6 text-gray-400' : 'font-medium text-gray-300'
                } ${
                  isActive
                    ? 'text-blue-400 bg-blue-500/15'
                    : 'hover:bg-gray-800/50 hover:text-blue-400'
                }`}
              >
                {item.text}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
