import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2.5 py-0.5 text-xs font-bold font-body transition-colors duration-150 ease focus:outline-none focus:ring-2 focus:ring-[var(--brand-accent)] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--border-default)]",
        secondary:
          "bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]",
        outline:
          "bg-transparent text-[var(--text-primary)] border border-[var(--border-default)]",
        destructive:
          "bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/30",
        success:
          "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30",
        warning:
          "bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
