import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap transition-all duration-150 ease focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-accent)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-accent)] rounded-lg font-heading font-semibold text-sm shadow-card border-none cursor-pointer",
        secondary:
          "bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-default)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] rounded-md font-body text-xs font-semibold cursor-pointer shadow-card",
        outline:
          "bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-default)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] rounded-md font-body text-xs font-semibold cursor-pointer shadow-card",
        ghost:
          "hover:bg-[var(--brand-accent-subtle)] text-[var(--text-primary)] hover:text-[var(--brand-accent)] rounded-md font-body text-xs font-semibold cursor-pointer",
        destructive:
          "bg-red-600 text-white hover:bg-red-700 rounded-lg font-heading text-xs font-semibold cursor-pointer shadow-card",
        link: "text-[var(--brand-primary)] underline-offset-4 hover:underline font-body font-semibold cursor-pointer",
      },
      size: {
        default: "h-10 px-4 py-2 rounded-lg",
        sm: "h-9 px-3 text-xs rounded-md",
        lg: "h-12 px-6 text-sm rounded-lg",
        icon: "h-10 w-10 rounded-md",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
