import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { Ticket, Users, Award, Calendar } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  open: '#f59e0b',
  'in progress': '#3b82f6',
  resolved: '#22c55e',
  closed: '#6b7280',
  waiting: '#8b5cf6',
  on_hold: '#ef4444',
};

const getStatusColor = (status: string) => STATUS_COLORS[status.toLowerCase()] || '#6b7280';

interface TicketStatsProps {
  ticket_by_status: { status: string; count: number }[];
  appointments_by_month: { month: string; appointments: number }[];
  tech_closed: { user_name: string; closed_count: number }[];
  top_customers: { customer_name: string; revenue: number }[];
}

export default function TicketStats({
  ticket_by_status,
  appointments_by_month,
  tech_closed,
  top_customers,
}: TicketStatsProps) {
  return (
    <>
      {/* Ticket by status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Ticket className="h-4 w-4 text-amber-400" /> Tickets by Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={ticket_by_status}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={(props: any) => `${props?.payload?.status || ''}: ${props?.payload?.count || 0}`
                }
                labelLine={true}
              >
                {ticket_by_status.map((entry) => (
                  <Cell key={entry.status} fill={getStatusColor(entry.status)} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Appointments by month */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Calendar className="h-4 w-4 text-purple-400" /> Appointments by Month
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={appointments_by_month}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11 }}
                stroke="var(--color-muted-foreground)"
              />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-card)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="appointments"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={{ fill: '#8b5cf6', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Tech Productivity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-400" /> Tech Productivity — Tickets Closed
          </CardTitle>
        </CardHeader>
        <CardContent>
          {tech_closed.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">No closed tickets yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, tech_closed.length * 50)}>
              <BarChart data={tech_closed} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-muted-foreground)"
                />
                <YAxis
                  type="category"
                  dataKey="user_name"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-muted-foreground)"
                  width={120}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                  }}
                />
                <Bar
                  dataKey="closed_count"
                  fill="#3b82f6"
                  radius={[0, 4, 4, 0]}
                  name="Closed Tickets"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Top Customers */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Award className="h-4 w-4 text-amber-400" /> Top Customers by Revenue
          </CardTitle>
        </CardHeader>
        <CardContent>
          {top_customers.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">No paid invoices yet</p>
          ) : (
            <div className="divide-y divide-border">
              {top_customers.map((c, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs font-medium text-muted-foreground w-5 shrink-0">
                      #{i + 1}
                    </span>
                    <span className="text-sm truncate">{c.customer_name}</span>
                  </div>
                  <span className="text-sm font-medium text-green-400 shrink-0">
                    ${c.revenue.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
