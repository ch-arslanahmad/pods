import { useState, type FormEvent } from 'react'
import { Background } from '../../components/Background'
import type { AppSettings } from './settings'

type SettingsProps = {
  settings: AppSettings
  onChange: (patch: Partial<AppSettings>) => void
  onBack: () => void
  onLogout: () => void
}

type Feedback = { tone: 'error' | 'success'; text: string } | null

export function Settings({
  settings,
  onChange,
  onBack,
  onLogout,
}: SettingsProps) {
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordFeedback, setPasswordFeedback] = useState<Feedback>(null)
  const [githubConnected, setGithubConnected] = useState(true)
  const [syncEnabled, setSyncEnabled] = useState(true)
  const [confirmingLogout, setConfirmingLogout] = useState(false)

  function togglePasswordForm() {
    setPasswordOpen((current) => !current)
    setPasswordFeedback(null)
  }

  function handlePassword(event: FormEvent) {
    event.preventDefault()
    if (currentPassword.trim() === '') {
      setPasswordFeedback({ tone: 'error', text: 'Enter your current password.' })
      return
    }
    if (newPassword.length < 8) {
      setPasswordFeedback({
        tone: 'error',
        text: 'The new password needs at least 8 characters.',
      })
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordFeedback({
        tone: 'error',
        text: 'The new passwords do not match.',
      })
      return
    }
    setPasswordFeedback({ tone: 'success', text: 'Password updated (demo).' })
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
  }

  return (
    <section className="view settings-view">
      <div className="view-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Settings</h1>
          <p className="view-subtitle">
            Account, connections, and dashboard preferences.
          </p>
        </div>
        <button type="button" className="button button-ghost" onClick={onBack}>
          ← Back to pods
        </button>
      </div>

      <div className="settings-grid">
        <section className="settings-card">
          <div className="settings-card-head">
            <div>
              <h2>Profile</h2>
              <p>How you appear in this workspace.</p>
            </div>
            <span className="settings-pill">Owner</span>
          </div>

          <div className="profile-row">
            <span className="profile-avatar" aria-hidden="true">
              OA
            </span>
            <div>
              <p className="profile-name">Ouwn Ch</p>
              <p className="profile-meta">Personal workspace</p>
            </div>
          </div>

          <dl className="settings-list">
            <div>
              <dt>Username</dt>
              <dd>@ouwn-ch</dd>
            </div>
            <div>
              <dt>Member since</dt>
              <dd>Nov 2026</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>Personal · 1 member</dd>
            </div>
          </dl>
        </section>

        <section className="settings-card">
          <div className="settings-card-head">
            <div>
              <h2>Login details</h2>
              <p>Credentials for this demo account.</p>
            </div>
            <span className="settings-pill">Demo</span>
          </div>

          <dl className="settings-list">
            <div>
              <dt>Email</dt>
              <dd>ouwn@example.com</dd>
            </div>
            <div>
              <dt>Password</dt>
              <dd>••••••••</dd>
            </div>
            <div>
              <dt>Two-factor</dt>
              <dd>
                <span className="status-pill is-on">Enabled</span>
              </dd>
            </div>
            <div>
              <dt>Last sign-in</dt>
              <dd>Today, 9:12 AM · this browser</dd>
            </div>
          </dl>

          <button
            type="button"
            className="button settings-action"
            onClick={togglePasswordForm}
          >
            {passwordOpen ? 'Cancel' : 'Change password'}
          </button>

          {passwordOpen && (
            <form className="settings-form" onSubmit={handlePassword}>
              <label className="field">
                <span className="field-label">Current password</span>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </label>
              <div className="field-row">
                <label className="field">
                  <span className="field-label">New password</span>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    autoComplete="new-password"
                  />
                </label>
                <label className="field">
                  <span className="field-label">Confirm password</span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    autoComplete="new-password"
                  />
                </label>
              </div>
              {passwordFeedback && (
                <p className={`form-${passwordFeedback.tone}`}>
                  {passwordFeedback.text}
                </p>
              )}
              <div className="form-actions">
                <button type="submit" className="button button-primary">
                  Update password
                </button>
              </div>
            </form>
          )}
        </section>

        <section className="settings-card settings-card-wide">
          <div className="settings-card-head">
            <div>
              <h2>GitHub connections</h2>
              <p>Link repositories so agents can read and write pod context.</p>
            </div>
            <span
              className={`status-pill ${githubConnected ? 'is-on' : 'is-off'}`}
            >
              {githubConnected ? 'Connected' : 'Not connected'}
            </span>
          </div>

          {githubConnected ? (
            <>
              <div className="github-card">
                <span className="github-mark" aria-hidden="true">
                  GH
                </span>
                <div className="github-text">
                  <p className="github-name">@ouwn-ch</p>
                  <p className="github-meta">
                    ch-arslanahmad/pods · connected via OAuth
                  </p>
                </div>
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => setGithubConnected(false)}
                >
                  Disconnect
                </button>
              </div>

              <label className="toggle-row">
                <span className="toggle-text">
                  <span className="toggle-label">Sync pod changes</span>
                  <span className="toggle-hint">
                    Push pod updates to the connected repository.
                  </span>
                </span>
                <Switch
                  checked={syncEnabled}
                  onChange={setSyncEnabled}
                  label="Sync pod changes"
                />
              </label>
            </>
          ) : (
            <div className="settings-empty">
              <p>Connect GitHub to link repositories and sync pod changes.</p>
              <button
                type="button"
                className="button button-primary"
                onClick={() => setGithubConnected(true)}
              >
                Connect GitHub
              </button>
            </div>
          )}
        </section>

        <section className="settings-card settings-card-wide">
          <div className="settings-card-head">
            <div>
              <h2>Preferences</h2>
              <p>Changes save automatically in this browser.</p>
            </div>
            <span className="settings-pill">Auto-saved</span>
          </div>

          <div className="toggle-list">
            <ToggleRow
              label="Email notifications"
              hint="Get an email when a pod is updated."
              checked={settings.emailNotifications}
              onChange={(value) => onChange({ emailNotifications: value })}
            />
            <ToggleRow
              label="Weekly digest"
              hint="A Monday summary of new pods and agent activity."
              checked={settings.weeklyDigest}
              onChange={(value) => onChange({ weeklyDigest: value })}
            />
            <ToggleRow
              label="Compact cards"
              hint="Tighter spacing on the pod grid."
              checked={settings.compactCards}
              onChange={(value) => onChange({ compactCards: value })}
            />
            <ToggleRow
              label="Reduce motion"
              hint="Turn off background and card animations."
              checked={settings.reduceMotion}
              onChange={(value) => onChange({ reduceMotion: value })}
            />
          </div>
        </section>

        <section className="settings-card settings-card-wide danger-card">
          <div className="settings-card-head">
            <div>
              <h2>Session</h2>
              <p>You are signed in on this browser.</p>
            </div>
            <span className="status-pill is-on">Active now</span>
          </div>

          <div className="session-row">
            <div>
              <p className="session-title">This browser · Linux</p>
              <p className="session-meta">
                Seed mode · no server session is created.
              </p>
            </div>
            <button
              type="button"
              className="button button-danger"
              onClick={() => setConfirmingLogout(true)}
            >
              Log out
            </button>
          </div>
        </section>
      </div>

      {confirmingLogout && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setConfirmingLogout(false)}
        >
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="logout-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="logout-title">Log out of Pods?</h2>
            <p>
              This demo session will close. You can sign back in immediately
              without entering credentials.
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setConfirmingLogout(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button-danger"
                onClick={onLogout}
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string
  hint: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <label className="toggle-row">
      <span className="toggle-text">
        <span className="toggle-label">{label}</span>
        <span className="toggle-hint">{hint}</span>
      </span>
      <Switch checked={checked} onChange={onChange} label={label} />
    </label>
  )
}

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
}) {
  return (
    <span className="switch">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-label={label}
      />
      <span className="switch-track" aria-hidden="true">
        <span className="switch-thumb" />
      </span>
    </span>
  )
}

export function SignedOut({ onSignIn }: { onSignIn: () => void }) {
  return (
    <div className="signed-out">
      <Background />
      <div className="signed-out-card">
        <span className="brand-mark signed-out-mark" aria-hidden="true">
          <span />
        </span>
        <p className="eyebrow">Pods</p>
        <h1>You're signed out</h1>
        <p>
          This is a demo session, so nothing was sent to a server. Sign back in
          to return to your pod library.
        </p>
        <button type="button" className="button button-primary" onClick={onSignIn}>
          Sign back in
        </button>
      </div>
    </div>
  )
}
