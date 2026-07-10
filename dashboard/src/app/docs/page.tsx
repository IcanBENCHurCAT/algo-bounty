import type { Metadata } from 'next';
import { readFileSync } from 'fs';
import { join } from 'path';
import DocsPageClient from './DocsPageClient';

// Read markdown content at build time (server component)
const CONTENT_PATH = join(process.cwd(), '..', 'docs', 'content.md');
const rawContent = readFileSync(CONTENT_PATH, 'utf-8');

// Extract table of contents from markdown headings (h2 and h3 only)
interface TOCItem {
  id: string;
  text: string;
  level: 2 | 3;
}

function extractTOC(content: string): TOCItem[] {
  const headings: TOCItem[] = [];
  const lines = content.split('\n');
  for (const line of lines) {
    const h3Match = line.match(/^### (.+)$/);
    const h2Match = line.match(/^## (.+)$/);
    if (h2Match) {
      headings.push({
        id: slugify(h2Match[1]),
        text: h2Match[1],
        level: 2,
      });
    } else if (h3Match) {
      headings.push({
        id: slugify(h3Match[1]),
        text: h3Match[1],
        level: 3,
      });
    }
  }
  return headings;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 60);
}

const tocItems = extractTOC(rawContent);

export const metadata: Metadata = {
  title: 'Documentation — AlgoBounty',
  description: 'AlgoBounty documentation: architecture, API reference, usage guide, and contribution guidelines.',
};

export default function DocsPage() {
  return <DocsPageClient rawContent={rawContent} tocItems={tocItems} />;
}
