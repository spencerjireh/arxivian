// Common types used throughout the application

export interface RouteParams {
  [key: string]: string | undefined
}

export interface ApiResponse<T = unknown> {
  data?: T
  error?: string
  message?: string
}



export interface Question {
  id: string
  question: string
  answer?: string
  createdAt: string
}