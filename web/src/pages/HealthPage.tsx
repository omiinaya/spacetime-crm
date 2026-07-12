import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { HeartPulse, RefreshCcw, Server, Database, Package } from 'lucide-react';

interface HealthCheck {
  server: string;
  stdb: string;
  module: string;
}

interface ReadyCheck {
  status: string;
}

const statusColor = (s: string) => {
  if (s === 'ok') return 'bg-green-500/10 text-green-500 border-green-500/20';
  if (s === 'unavailable') return 'bg-red-500/10 text-red-500 border-red-500/20';
  return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
};

const statusDot = (s: string) => {
  if (s === 'ok') return 'bg-green-500';
  if (s === 'unavailable') return 'bg-red-500';
  return 'bg-amber-500';
};

export default function HealthPage() {
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [ready, setReady] = useState<ReadyCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, r] = await Promise.all([api.health.check(), api.health.ready()]);
      setHealth(h);
      setReady(r);
    } catch (e: any) {
      setError(e?.message || 'Health check failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, [check]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Health &amp; Monitoring</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Service status and connectivity checks
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={check} disabled={loading}>
          <RefreshCcw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/50">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Server */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              <CardTitle className="text-sm">API Server</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading && !health ? (
              <p className="text-sm text-muted-foreground">Checking...</p>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${statusDot(health?.server || 'unknown')}`}
                  />
                  <Badge variant="outline" className={statusColor(health?.server || 'unknown')}>
                    {health?.server || 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  FastAPI backend on port {window.location.port || 8723}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* STDB */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              <CardTitle className="text-sm">SpacetimeDB</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading && !health ? (
              <p className="text-sm text-muted-foreground">Checking...</p>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${statusDot(health?.stdb || 'unknown')}`}
                  />
                  <Badge variant="outline" className={statusColor(health?.stdb || 'unknown')}>
                    {health?.stdb || 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Database: spacetime-crm on port 3001
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Module */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Package className="h-5 w-5 text-primary" />
              <CardTitle className="text-sm">STDB Module</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {loading && !health ? (
              <p className="text-sm text-muted-foreground">Checking...</p>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${statusDot(health?.module || 'unknown')}`}
                  />
                  <Badge variant="outline" className={statusColor(health?.module || 'unknown')}>
                    {health?.module || 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">CRM module with 18 tables</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Readiness probe */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Readiness Probe</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <HeartPulse
              className={`h-6 w-6 ${ready?.status === 'ok' ? 'text-green-500' : 'text-red-500'}`}
            />
            <div>
              <Badge variant="outline" className={statusColor(ready?.status || 'unknown')}>
                {ready?.status || 'unknown'}
              </Badge>
              <p className="text-xs text-muted-foreground mt-1">
                {ready?.status === 'ok'
                  ? 'All systems operational'
                  : 'STDB is not reachable — some features may be unavailable'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Diagnostics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <p className="text-muted-foreground">API Endpoint</p>
            <p className="font-mono text-xs">{window.location.origin}/api/health</p>
          </div>
          <div>
            <p className="text-muted-foreground">Auto-refresh</p>
            <p>Every 30 seconds</p>
          </div>
          <div>
            <p className="text-muted-foreground">Last checked</p>
            <p>{new Date().toLocaleTimeString()}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
