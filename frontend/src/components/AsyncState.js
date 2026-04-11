import { AlertCircle, CheckCircle2, Info, Loader2 } from "lucide-react"

const STATE_MAP = {
  loading: {
    icon: Loader2,
    title: "Loading",
    className: "is-loading",
  },
  error: {
    icon: AlertCircle,
    title: "Something went wrong",
    className: "is-error",
  },
  empty: {
    icon: Info,
    title: "No data found",
    className: "is-empty",
  },
  success: {
    icon: CheckCircle2,
    title: "Done",
    className: "is-success",
  },
}

const AsyncState = ({
  variant = "loading",
  title,
  message,
  actionLabel,
  onAction,
  className = "",
}) => {
  const config = STATE_MAP[variant] || STATE_MAP.loading
  const Icon = config.icon
  const resolvedTitle = title || config.title

  return (
    <section className={`async-state ${config.className} ${className}`.trim()} role="status" aria-live="polite">
      <div className="async-state-icon-wrap" aria-hidden>
        <Icon size={22} className={variant === "loading" ? "async-spin" : ""} />
      </div>

      <div className="async-state-copy">
        <h2>{resolvedTitle}</h2>
        {message ? <p>{message}</p> : null}
      </div>

      {actionLabel && typeof onAction === "function" ? (
        <button className="btn btn-secondary" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </section>
  )
}

export default AsyncState