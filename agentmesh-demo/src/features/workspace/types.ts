import type { components } from '../../api/generated/schema'

export type WorkspaceScope = {
  userId: string
  workspaceId: string
  projectId: string
}

export type ChatThread = components['schemas']['ChatThread']
export type Source = components['schemas']['Source']
export type SearchResult = components['schemas']['SearchResult']
export type ChatWorkflowTrace = Omit<components['schemas']['ChatWorkflowTrace'], 'provider'> & {
  requested_provider?: string | null
  actual_provider?: string | null
  provider_mode?: 'real' | 'fallback' | null
  latency_ms?: number | null
}
export type ChatMessage = components['schemas']['ChatMessage'] & {
  workflow_trace?: ChatWorkflowTrace | null
}
export type ChatResponse = Omit<components['schemas']['ChatResponse'], 'user_message' | 'assistant_message'> & {
  user_message: ChatMessage
  assistant_message: ChatMessage
  workflow_trace?: ChatWorkflowTrace | null
}

export type ChatTurnReceipt = {
  client_turn_id: string
  status: 'processing' | 'completed' | 'failed'
  thread_id: string
  response?: ChatResponse | null
}

export type ThreadListResponse = { items: ChatThread[] }
export type ThreadDetailResponse = { thread: ChatThread; messages: ChatMessage[] }
export type Skill = {
  command: string
  title: string
  description: string
  usage: string
  placeholder: string
  aliases: string[]
  requires_input: boolean
}
export type SkillsResponse = { items: Skill[] }

export type DocumentRecord = {
  id: string
  title: string
  file_name: string
  content_type: string
  text: string
  source: Source
  workspace_id: string
  project_id: string
  uploaded_by: string
  metadata: Record<string, string>
  version: number
  expected_chunks: number
  completed_chunks: number
  created_at: string
  updated_at: string
}

export type DocumentJobStatus = 'queued' | 'running' | 'completed' | 'failed'
export type DocumentJob = {
  id: string
  file_name: string
  content_type: string
  workspace_id: string
  project_id: string
  uploaded_by: string
  status: DocumentJobStatus
  document_id?: string | null
  version: number
  expected_chunks: number
  completed_chunks: number
  error?: string | null
  error_type?: string | null
  created_at: string
  updated_at: string
}

export type UploadResponse = { item: DocumentRecord; job?: never } | { item?: never; job: DocumentJob }
export type DocumentJobsResponse = { items: DocumentJob[] }
export type DocumentJobResponse = { item: DocumentJob }
export type DocumentResponse = { item: DocumentRecord }
export type SearchResponse = { items: SearchResult[] }

export type ResourceSelection =
  | { kind: 'document'; id: string }
  | { kind: 'source'; source: Source }
