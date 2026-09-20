import type { FeedItem, FeedResponse } from '../../src/types/api'

export function makeFeedItem(overrides: Partial<FeedItem> = {}): FeedItem {
  return {
    paper: {
      arxiv_id: '2401.00001',
      title: 'Attention Is All You Need',
      authors: ['Vaswani', 'Shazeer', 'Parmar', 'Uszkoreit'],
      categories: ['cs.CL', 'cs.AI'],
      published_date: '2024-01-15T00:00:00Z',
      pdf_url: 'https://arxiv.org/pdf/2401.00001',
    },
    scores: {
      method_clarity: 80,
      resource_feasibility: 50,
      data_availability: 100,
      demand: 85,
      composite: 71,
    },
    verdict: 'Transformer for machine translation; one datacenter GPU; public data',
    signals: {
      pseudocode_present: true,
      public_datasets: true,
      single_gpu: true,
      code_released: false,
      compute_match: null,
    },
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
