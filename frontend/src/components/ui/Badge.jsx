import React from 'react';

/**
 * Reusable Badge Component for VisionCare
 * Variants: emerald | slate | amber | red | blue
 */
export default function Badge({
  children,
  variant = 'emerald',
  size = 'md',
  className = '',
  icon: Icon,
  ...props
}) {
  const variantStyles = {
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    red: 'bg-rose-50 text-rose-700 border-rose-200',
    blue: 'bg-sky-50 text-sky-700 border-sky-200',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 rounded-md gap-1',
    md: 'text-xs px-2.5 py-1 rounded-lg gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1 rounded-lg gap-2 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center border ${variantStyles[variant] || variantStyles.emerald} ${
        sizeStyles[size] || sizeStyles.md
      } ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
      <span>{children}</span>
    </span>
  );
}

