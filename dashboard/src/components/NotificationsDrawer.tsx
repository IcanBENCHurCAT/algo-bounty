'use client'

import React, { useCallback, useEffect, useState } from 'react'
import type { NotificationItem } from '@/types'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const EVENT_ICONS: Record<string, string> = {
  'bounty.created':   '🎯',
  'bounty.claimed':   '🤝',
  'bounty.submitted': '📬',
  'bounty.approved':  '✅',
  'bounty.rejected':  '❌',
  'bounty.disputed':  '⚖️',
  'karma.updated':    '⭐',
}

interface NotificationsDrawerProps {
  open: boolean
  onClose: () => void
}

export function NotificationsDrawer({ open, onClose }: NotificationsDrawerProps) {
  const { jwt, connected } = useAuth()
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(false)

  const unreadCount = notifications.filter((n) => !n.read).length

  const fetchNotifications = useCallback(async () => {
    if (!jwt) return
    setLoading(true)
    try {
      const items = await getNotifications(jwt)
      setNotifications(items)
    } catch {
      // silently ignore
    } finally {
      setLoading(false)
    }
  }, [jwt])

  useEffect(() => {
    if (open && connected) {
      void fetchNotifications()
    }
  }, [open, connected, fetchNotifications])

  const handleMarkRead = async (id: number) => {
    if (!jwt) return
    await markNotificationRead(id, jwt)
    setNotifications((prev) =>
      prev.map((n) => (n.notification_id === id ? { ...n, read: true } : n)),
    )
  }

  const handleMarkAllRead = async () => {
    if (!jwt) return
    await markAllNotificationsRead(jwt)
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            backdropFilter: 'blur(4px)',
            zIndex: 100,
          }}
        />
      )}

      {/* Drawer */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 'min(400px, 100vw)',
          background: 'rgba(8,8,18,0.98)',
          backdropFilter: 'blur(24px)',
          borderLeft: '1px solid rgba(255,255,255,0.08)',
          zIndex: 101,
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700, color: '#f1f5f9' }}>
              Notifications
            </h2>
            {unreadCount > 0 && (
              <span
                style={{
                  padding: '0.125rem 0.5rem',
                  borderRadius: '9999px',
                  background: 'rgba(99,102,241,0.2)',
                  color: '#818cf8',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {unreadCount}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {unreadCount > 0 && (
              <Button variant="ghost" size="sm" onClick={() => void handleMarkAllRead()}>
                Mark all read
              </Button>
            )}
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                fontSize: '1.25rem',
                padding: '0.25rem',
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
              <Spinner />
            </div>
          )}

          {!loading && notifications.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                padding: '3rem 1rem',
                color: '#475569',
                fontSize: '0.9375rem',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔔</div>
              No notifications yet
            </div>
          )}

          {notifications.map((n) => (
            <div
              key={n.notification_id}
              onClick={() => !n.read && void handleMarkRead(n.notification_id)}
              style={{
                display: 'flex',
                gap: '0.875rem',
                padding: '0.875rem 1rem',
                borderRadius: '0.75rem',
                marginBottom: '0.375rem',
                background: n.read ? 'transparent' : 'rgba(99,102,241,0.06)',
                border: n.read ? '1px solid transparent' : '1px solid rgba(99,102,241,0.12)',
                cursor: n.read ? 'default' : 'pointer',
                transition: 'background 0.15s',
              }}
            >
              <span style={{ fontSize: '1.25rem', flexShrink: 0, marginTop: '0.125rem' }}>
                {EVENT_ICONS[n.event_type] ?? '📢'}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.875rem', color: '#cbd5e1', marginBottom: '0.25rem', fontWeight: n.read ? 400 : 600 }}>
                  {n.event_type.replace('.', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </div>
                {n.data.bounty_id && (
                  <div style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'monospace' }}>
                    {String(n.data.bounty_id)}
                  </div>
                )}
                <div style={{ fontSize: '0.6875rem', color: '#334155', marginTop: '0.375rem' }}>
                  {timeAgo(n.created_at)}
                </div>
              </div>
              {!n.read && (
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: '#6366f1',
                    flexShrink: 0,
                    marginTop: '0.375rem',
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
