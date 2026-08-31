import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  Chip,
} from '@mui/material';
import {
  People as PeopleIcon,
  AccessTime as AccessTimeIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { attendanceAPI } from '../services/api';

const REFRESH_MS = 10000;

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
}

function StatCard({ title, value, icon, color, bgColor }: StatCardProps) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="body2" sx={{ color: '#718096', mb: 0.5, fontWeight: 500, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#1a202c' }}>
              {value}
            </Typography>
          </Box>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '12px',
              backgroundColor: bgColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: color,
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['attendanceStats'],
    queryFn: () => attendanceAPI.getStats().then((res) => res.data),
    refetchInterval: REFRESH_MS,
  });

  const { data: liveFeed } = useQuery({
    queryKey: ['liveAttendanceFeed'],
    queryFn: () => attendanceAPI.getLiveFeed(15).then((res) => res.data),
    refetchInterval: REFRESH_MS,
  });

  const events = liveFeed?.events || [];

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>
          Dashboard
        </Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Overview of today's attendance activity
        </Typography>
      </Box>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Total Employees"
            value={stats?.total_employees || 0}
            icon={<PeopleIcon />}
            color="#2b6cb0"
            bgColor="#ebf4ff"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Present Today"
            value={stats?.present_today || 0}
            icon={<CheckCircleIcon />}
            color="#2f855a"
            bgColor="#f0fff4"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Absent Today"
            value={stats?.absent_today || 0}
            icon={<WarningIcon />}
            color="#c53030"
            bgColor="#fff5f5"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Late Today"
            value={stats?.late_today || 0}
            icon={<AccessTimeIcon />}
            color="#c05621"
            bgColor="#fffaf0"
          />
        </Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h6">Live Activity</Typography>
            <Chip label="Auto-refresh 10s" size="small" sx={{ backgroundColor: '#ebf4ff', color: '#2b6cb0', fontWeight: 600, fontSize: '0.7rem' }} />
          </Box>
          {events.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#718096' }}>
              No recent activity yet. Activity will appear here as employees check in and out.
            </Typography>
          ) : (
            <List disablePadding>
              {events.map((e: any) => (
                <ListItem key={e.id} disableGutters divider sx={{ py: 1 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <Avatar sx={{ width: 32, height: 32, bgcolor: e.event_type === 'CHECK_IN' ? '#2f855a' : '#c53030' }}>
                      {e.event_type === 'CHECK_IN' ? <LoginIcon fontSize="small" /> : <LogoutIcon fontSize="small" />}
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{e.employee_name || 'Unknown'}</Typography>
                        <Typography variant="caption" sx={{ color: '#a0aec0', fontFamily: 'monospace' }}>{e.employee_code}</Typography>
                        <Chip
                          label={e.event_type === 'CHECK_IN' ? 'CHECK-IN' : 'CHECK-OUT'}
                          size="small"
                          sx={{ backgroundColor: e.event_type === 'CHECK_IN' ? '#f0fff4' : '#fff5f5', color: e.event_type === 'CHECK_IN' ? '#2f855a' : '#c53030', fontWeight: 600, fontSize: '0.6rem', height: 20 }}
                        />
                      </Box>
                    }
                    secondary={e.event_time ? new Date(e.event_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) : ''}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
