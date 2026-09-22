// Curated arXiv categories for the onboarding picker (the backend accepts any valid id).

export interface ArxivCategory {
  id: string
  label: string
}

export const ARXIV_CATEGORIES: ArxivCategory[] = [
  { id: 'cs.AI', label: 'Artificial intelligence' },
  { id: 'cs.LG', label: 'Machine learning' },
  { id: 'cs.CL', label: 'Computation and language' },
  { id: 'cs.CV', label: 'Computer vision' },
  { id: 'cs.RO', label: 'Robotics' },
  { id: 'cs.IR', label: 'Information retrieval' },
  { id: 'cs.NE', label: 'Neural and evolutionary computing' },
  { id: 'cs.SE', label: 'Software engineering' },
  { id: 'cs.DC', label: 'Distributed computing' },
  { id: 'cs.CR', label: 'Cryptography and security' },
  { id: 'cs.DB', label: 'Databases' },
  { id: 'cs.HC', label: 'Human-computer interaction' },
  { id: 'cs.SD', label: 'Sound' },
  { id: 'stat.ML', label: 'Statistics: machine learning' },
  { id: 'eess.AS', label: 'Audio and speech processing' },
  { id: 'eess.IV', label: 'Image and video processing' },
  { id: 'eess.SP', label: 'Signal processing' },
  { id: 'math.OC', label: 'Optimization and control' },
]

export const MAX_KEYWORDS = 10
export const MAX_KEYWORD_LENGTH = 50
