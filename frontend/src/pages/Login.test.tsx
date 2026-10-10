import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Login from './Login'
import * as auth from '../auth/AuthContext'
import { ApiError } from '../api/client'

vi.mock('../auth/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(auth.useAuth)

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Login />
    </MemoryRouter>,
  )
}

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the sign-in form', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderLogin()
    expect(screen.getByRole('form', { name: /sign in form/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('submits credentials on sign in', async () => {
    const login = vi.fn().mockResolvedValue(undefined)
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
      user: null,
      login,
      logout: vi.fn(),
    })
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'e@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(login).toHaveBeenCalledWith('e@x.com', 'secret'))
  })

  it('shows the API error message when sign in fails', async () => {
    const login = vi.fn().mockRejectedValue(new ApiError(401, 'invalid_credentials', 'Bad credentials'))
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
      user: null,
      login,
      logout: vi.fn(),
    })
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'e@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Bad credentials'),
    )
  })

  it('shows a generic message when the server is unreachable', async () => {
    const login = vi.fn().mockRejectedValue(new Error('network down'))
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
      user: null,
      login,
      logout: vi.fn(),
    })
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'e@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/unable to reach the server/i),
    )
  })
})
