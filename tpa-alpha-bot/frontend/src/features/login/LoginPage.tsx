import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'
import { ArrowRight } from 'lucide-react'
import { adminAPI } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await adminAPI.login(password)
      localStorage.setItem('admin_token', response.token)
      localStorage.setItem('token_expires_at', response.expires_at)
      navigate('/dashboard')
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>
      setError(axiosError.response?.data?.detail || 'Login failed')
      setPassword('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#05070b_0%,#070a0f_55%,#05070b_100%)]" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="w-full max-w-lg">
          <div className="mb-8 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.42em] text-accent/80">
              TPA ALPHA
            </p>
            <h1 className="mt-4 text-5xl font-semibold tracking-[-0.05em] text-white sm:text-6xl">
              Admin login
            </h1>
            <p className="mt-3 text-base leading-7 text-slate-300">Access the control panel.</p>
          </div>

          <Card className="border-white/10 bg-slate-950/82 shadow-[0_24px_80px_rgba(0,0,0,0.38)] backdrop-blur-xl">
            <CardContent className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                {error ? (
                  <Alert variant="destructive" title="Unable to sign in">
                    {error}
                  </Alert>
                ) : null}

                <Input
                  id="password"
                  label="Admin Password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  disabled={loading}
                  autoFocus
                  required
                  className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                />

                <Button
                  type="submit"
                  size="lg"
                  disabled={!password.trim() || loading}
                  isLoading={loading}
                  className="h-14 w-full rounded-2xl bg-accent text-accent-foreground shadow-lg shadow-accent/20 hover:bg-accent/90"
                >
                  <ArrowRight className="mr-2 size-4" />
                  {loading ? 'Signing in...' : 'Access dashboard'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
