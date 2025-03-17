import * as React from "react"
import * as SwitchPrimitives from "@radix-ui/react-switch"

export interface SwitchProps extends React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root> {
  size?: "default" | "sm"
  className?: string
}

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  SwitchProps
>(({ className = "", size = "default", ...props }, ref) => (
  <SwitchPrimitives.Root
    className={`peer inline-flex h-${size === "sm" ? "4" : "6"} w-${size === "sm" ? "8" : "11"} shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input ${className}`}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={`pointer-events-none block h-${size === "sm" ? "3" : "5"} w-${size === "sm" ? "3" : "5"} rounded-full bg-background shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-${size === "sm" ? "4" : "5"} data-[state=unchecked]:translate-x-0`}
    />
  </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
