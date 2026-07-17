'use client'

/**
 * Modal — Accessible modal dialog wrapper (WCAG 2.1 AA).
 *
 * Features:
 * - role="dialog" + aria-modal="true" + aria-labelledby/aria-describedby
 * - Focus trap: Tab/Shift+Tab cycles within modal content
 * - Escape key closes modal (if onClose provided)
 * - Body scroll lock while open
 * - Backdrop click closes modal (if onClose provided)
 * - Focuses first focusable element on open
 *
 * FR-009: Accessibility compliance
 */

import { useEffect, useRef, useCallback } from 'react'

interface ModalProps {
  open: boolean
  onClose?: () => void
  titleId: string
  children: React.ReactNode
  ariaLabelledBy?: string
  ariaDescribedBy?: string
}

function getFocusableElements(container: HTMLElement) {
  return Array.from(
    container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
  )
}

export function Modal({ open, onClose, titleId, children, ariaLabelledBy, ariaDescribedBy }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  // Save current focus on mount, restore on close
  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement
      document.body.style.overflow = 'hidden'

      // Focus first focusable element
      setTimeout(() => {
        const modal = modalRef.current
        if (modal) {
          const focusable = getFocusableElements(modal)
          if (focusable.length > 0) {
            ;(focusable[0] as HTMLElement).focus()
          }
        }
      }, 50)
    }

    return () => {
      document.body.style.overflow = ''
      if (previousFocusRef.current) {
        previousFocusRef.current.focus()
      }
    }
  }, [open])

  // Focus trap + Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!open) return

      // Escape key closes
      if (e.key === 'Escape' && onClose) {
        e.preventDefault()
        onClose()
        return
      }

      // Tab trap
      if (e.key === 'Tab') {
        const modal = modalRef.current
        if (modal) {
          const focusable = getFocusableElements(modal)
          if (focusable.length === 0) return

          const first = focusable[0]
          const last = focusable[focusable.length - 1]

          if (e.shiftKey) {
            // Shift+Tab: if on first element, wrap to last
            if (document.activeElement === first) {
              e.preventDefault()
              ;(last as HTMLElement).focus()
            }
          } else {
            // Tab: if on last element, wrap to first
            if (document.activeElement === last) {
              e.preventDefault()
              ;(first as HTMLElement).focus()
            }
          }
        }
      }
    },
    [open, onClose]
  )

  useEffect(() => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, handleKeyDown])

  if (!open) return null

  const labelledBy = ariaLabelledBy || titleId
  const describedBy = ariaDescribedBy

  return (
    <div
      role="presentation"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.7)',
        padding: '1rem',
      }}
      onClick={onClose ? (e) => {
        if (e.target === e.currentTarget) onClose()
      } : undefined}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        {...(describedBy ? { 'aria-describedby': describedBy } : {})}
        style={{
          background: '#0f172a',
          border: '1px solid rgba(99,102,241,0.3)',
          borderRadius: '1rem',
          maxWidth: '480px',
          width: '100%',
          padding: '1.5rem',
          color: '#e2e8f0',
          // Responsive: allow full height on small screens
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
      >
        {children}
      </div>
    </div>
  )
}
