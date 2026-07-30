"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";
import { C } from "@/lib/constants";
import { Svg, IconName } from "./icons";

type Variant = "primary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: IconName;
  iconSize?: number;
  iconSw?: number;
  iconFill?: string;
  /** When set, the button renders as an anchor linking to this URL. */
  href?: string;
  children: ReactNode;
}

/** Button — primary (blue CTA) or ghost (white with border).
 *
 *  Pass `href` to render as an `<a>` that navigates, preserving the same
 *  visual styles (used by dashboard CTAs that route to /practice, etc.). */
export function Button({
  variant = "primary",
  icon,
  iconSize = 14,
  iconSw = 1.8,
  iconFill,
  href,
  children,
  style,
  ...props
}: ButtonProps) {
  const isPrimary = variant === "primary";

  const inner = (
    <>
      {icon && (
        <Svg
          icon={icon}
          size={iconSize}
          col={isPrimary ? "#fff" : C.sec}
          sw={isPrimary ? 0 : iconSw}
          fill={iconFill ?? (isPrimary ? "none" : "none")}
        />
      )}
      {children}
    </>
  );

  const sharedStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: isPrimary ? "0.75rem 1.25rem" : "0.75rem 1.125rem",
    borderRadius: 10,
    border: isPrimary ? "none" : `1px solid ${C.bdr}`,
    background: isPrimary ? C.mid : C.surf,
    color: isPrimary ? "#fff" : C.sec,
    fontSize: isPrimary ? "0.9rem" : "0.875rem",
    fontWeight: isPrimary ? 600 : 500,
    fontFamily: "Inter, sans-serif",
    letterSpacing: isPrimary ? "-0.01em" : undefined,
    textDecoration: "none",
    cursor: "pointer",
    ...style,
  };

  if (href) {
    return (
      <a className={isPrimary ? "btn-primary" : "btn-ghost"} href={href} style={sharedStyle}>
        {inner}
      </a>
    );
  }

  return (
    <button
      className={isPrimary ? "btn-primary" : "btn-ghost"}
      style={sharedStyle}
      {...props}
    >
      {inner}
    </button>
  );
}
