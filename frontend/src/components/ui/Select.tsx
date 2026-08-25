type SelectOption = {
  value: string
  label: string
}

type SelectProps = {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  disabled?: boolean
  placeholder?: string
}

export function Select({
  id,
  label,
  value,
  onChange,
  options,
  disabled = false,
  placeholder,
}: SelectProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:opacity-60"
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
