type ErrorAlertProps = {
  message: string
}

export function ErrorAlert({ message }: ErrorAlertProps) {
  return (
    <p className="text-sm text-red-600" role="alert">
      {message}
    </p>
  )
}
