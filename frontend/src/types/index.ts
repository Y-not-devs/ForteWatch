export interface MetaFeatures {
  auth: boolean
  uploads: boolean
}

export interface AppMeta {
  app_name: string
  environment: string
  features: MetaFeatures
}

export interface User {
  id: number
  email: string
  name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface UploadFileItem {
  name: string
  url: string
  size: number
  content_type: string
  created_at: string
}
