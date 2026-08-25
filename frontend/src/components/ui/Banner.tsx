import type { ReactNode } from 'react'

type BannerProps = {
  message: string
  children?: ReactNode
  action?: ReactNode
}

export function Banner({ message, children, action }: BannerProps) {
  const slot = action ?? children

  return (
    <div
      className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
      role="status"
    >
      <p>{message}</p>
      {slot && <div className="mt-2">{slot}</div>}
    </div>
  )
}
