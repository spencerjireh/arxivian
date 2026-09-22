import type { FeedItem, FeedResponse, LibraryResponse, PaperMetadata } from '../../src/types/api'

export function makePaperMetadata(overrides: Partial<PaperMetadata> = {}): PaperMetadata {
  return {
    arxiv_id: '2401.00001',
    title: 'Attention Is All You Need',
    authors: ['Vaswani', 'Shazeer', 'Parmar', 'Uszkoreit'],
    abstract: 'We propose a new simple network architecture, the Transformer.',
    categories: ['cs.CL', 'cs.AI'],
    published_date: '2024-01-15T00:00:00Z',
    pdf_url: 'https://arxiv.org/pdf/2401.00001',
    ...overrides,
  }
}

export function makeFeedItem(overrides: Partial<FeedItem> = {}): FeedItem {
  const { arxiv_id, title, authors, categories, published_date, pdf_url } = makePaperMetadata()
  return {
    paper: { arxiv_id, title, authors, categories, published_date, pdf_url },
    scores: {
      method_clarity: 80,
      resource_feasibility: 50,
      data_availability: 100,
      demand: 85,
      composite: 71,
    },
    headline: 'Transformer for machine translation',
    meta: ['one datacenter GPU', 'public data', 'pseudocode given'],
    compute_match: null,
    low_confidence: [],
    keyword_match: false,
    state: null,
    scored_at: '2026-08-04T00:00:00Z',
    ...overrides,
  }
}

export function makeFeedResponse(
  items: FeedItem[],
  overrides: Partial<FeedResponse> = {}
): FeedResponse {
  return {
    week_start: '2026-08-03',
    available_weeks: [{ week_start: '2026-08-03', paper_count: items.length }],
    categories_available: ['cs.AI', 'cs.CL', 'cs.LG'],
    total: items.length,
    offset: 0,
    limit: 20,
    items,
    ...overrides,
  }
}

export function makeLibraryResponse(overrides: Partial<LibraryResponse> = {}): LibraryResponse {
  return { saved: [], implementing: [], shipped: [], ...overrides }
}
