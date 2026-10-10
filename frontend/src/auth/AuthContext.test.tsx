import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import * as client from '../api/client'

vi.mock('../api/client', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn(),
  clearTokens: vi.fn(),
  setAccessToken: vi.fn(),
  setRefreshToken: vi.fn(),
  getRefreshToken: vi.fn(),
}))

const mockUser = { id: 'u1', email: 'e@x.com', username: 'eve', active: true }

function AuthDisplay() {
  const { user, loading, isAuthenticated, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authed">{String(isAuthenticated)}</span>
      <span data-testid="user">{user ? user.email : 'none'}</span>
      <button onClick={() => void login('e@x.com', 'pw')}>login</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  )
}

function renderAuth() {
  return render(
    <AuthProvider>
      <AuthDisplay />
    </AuthProvider>,
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('starts unauthenticated when there is no stored token', async () => {
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('authed')).toHaveTextContent('false')
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('loads the current user from a stored token', async () => {
    localStorage.setItem('oc_access_token', 'stored')
    vi.mocked(client.getMe).mockResolvedValue(mockUser)
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(client.getMe).toHaveBeenCalled()
    expect(screen.getByTestId('user')).toHaveTextContent('e@x.com')
    expect(screen.getByTestId('authed')).toHaveTextContent('true')
  })

  it('clears the session when the stored token is invalid', async () => {
    localStorage.setItem('oc_access_token', 'stored')
    vi.mocked(client.getMe).mockRejectedValue(new Error('nope'))
    renderAuth()
    await waitFor(() => expect(client.clearTokens).toHaveBeenCalled())
  })

  it('logs in with credentials and stores the user', async () => {
    vi.mocked(client.login).mockResolvedValue({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
      expires_in: 3600,
    })
    vi.mocked(client.getMe).mockResolvedValue(mockUser)
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    await userEvent.click(screen.getByText('login'))
    expect(client.login).toHaveBeenCalledWith('e@x.com', 'pw')
    expect(client.setAccessToken).toHaveBeenCalledWith('a')
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('e@x.com'))
    expect(screen.getByTestId('authed')).toHaveTextContent('true')
  })

  it('logs out and clears the user', async () => {
    vi.mocked(client.getRefreshToken).mockReturnValue('r')
    vi.mocked(client.logout).mockResolvedValue(undefined)
    // Seed an authenticated state by giving a valid stored token + user.
    localStorage.setItem('oc_access_token', 'stored')
    vi.mocked(client.getMe).mockResolvedValue(mockUser)
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('authed')).toHaveTextContent('true'))
    await userEvent.click(screen.getByText('logout'))
    expect(client.logout).toHaveBeenCalledWith('r')
    expect(client.clearTokens).toHaveBeenCalled()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
    expect(screen.getByTestId('authed')).toHaveTextContent('false')
  })
})
