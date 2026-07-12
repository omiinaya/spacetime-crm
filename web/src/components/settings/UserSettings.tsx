import { Plus, Settings, User as UserIcon } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../../lib/query-client';
import { api, User } from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';

export default function UserSettings() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', role: 'staff' });

  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await api.users.list();
      return res.users ?? [];
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; email: string; role: string }) => api.users.create(data),
    onSuccess: () => {
      toast.success('User created');
      setShowForm(false);
      setForm({ name: '', email: '', role: 'staff' });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      toast.error('Failed to create user');
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Users</CardTitle>
        <Button size="sm" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Add User
        </Button>
      </CardHeader>
      <CardContent>
        {showForm && (
          <div className="flex gap-2 mb-4 p-3 rounded bg-muted/50">
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Input
              placeholder="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <Select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-32"
            >
              <option value="admin">Admin</option>
              <option value="tech">Tech</option>
              <option value="staff">Staff</option>
            </Select>
            <Button size="sm" onClick={() => createMutation.mutate(form)}>
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
          </div>
        )}
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <UserIcon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">{u.name}</p>
                  <p className="text-xs text-muted-foreground">{u.email}</p>
                </div>
              </div>
              <Badge variant={u.active ? 'success' : 'secondary'}>{u.role}</Badge>
              <span className="text-xs text-muted-foreground">PIN: {u.pin || '-'}</span>
              <span className="text-xs text-muted-foreground">
                2FA: {u.totp_enabled ? 'ON' : 'OFF'}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
