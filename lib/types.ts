export type Profile = {
  id: string
  full_name: string
  headline: string | null
  bio: string | null
  location: string | null
  avatar_url: string | null
  roles: string[]
  created_at: string
  updated_at: string
}

export type Credit = {
  id: string
  profile_id: string
  project_title: string
  role_on_project: string
  project_year: number | null
  project_type: string | null
  created_at: string
}

export type ConnectionStatus = 'pending' | 'accepted'

export type Connection = {
  id: string
  requester_id: string
  addressee_id: string
  status: ConnectionStatus
  created_at: string
}
