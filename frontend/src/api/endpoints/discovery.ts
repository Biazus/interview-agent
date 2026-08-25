import type { ApiClient } from '../client.ts'

export function getDomains(client: ApiClient): Promise<string[]> {
  return client.request<string[]>('GET', '/domains')
}

export function getTopics(client: ApiClient, domain: string): Promise<string[]> {
  return client.request<string[]>(
    'GET',
    `/topics?domain=${encodeURIComponent(domain)}`,
  )
}
