type TextareaProps = {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  maxLength?: number
  disabled?: boolean
}

export function Textarea({
  id,
  label,
  value,
  onChange,
  maxLength,
  disabled = false,
}: TextareaProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        disabled={disabled}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        rows={6}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:opacity-60"
      />
    </div>
  )
}
