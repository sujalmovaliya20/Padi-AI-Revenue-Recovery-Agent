import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 py-2 font-body text-xs font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus-visible:outline-none focus-visible:border-[var(--brand-accent)] focus-visible:ring-1 focus-visible:ring-[var(--brand-accent)] disabled:cursor-not-allowed disabled:opacity-50 transition-colors duration-150 ease",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
