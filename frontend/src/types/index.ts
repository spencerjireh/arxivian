// Common types used throughout the application

export interface RouteParams {
  [key: string]: string | undefined
}

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export interface Document {
  id: string
  title: string
  content?: string
  createdAt: string
  updatedAt: string
}

export interface SearchResult {
  id: string
  title: string
  snippet: string
  score: number
}

export interface Question {
  id: string
  question: string
  answer?: string
  createdAt: string
}