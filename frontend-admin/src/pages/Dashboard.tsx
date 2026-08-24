import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
} from '@mui/material';
import {
  People as PeopleIcon,
  AccessTime as AccessTimeIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { attendanceAPI } from '../services/api';

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
  });

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
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Employees"
            value={stats?.total_employees || 0}
            icon={<PeopleIcon />}
            color="#2b6cb0"
            bgColor="#ebf4ff"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Present Today"
            value={stats?.present_today || 0}
            icon={<CheckCircleIcon />}
            color="#2f855a"
            bgColor="#f0fff4"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Absent Today"
            value={stats?.absent_today || 0}
            icon={<WarningIcon />}
            color="#c53030"
            bgColor="#fff5f5"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
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
          <Typography variant="h6" sx={{ mb: 1 }}>
            Recent Activity
          </Typography>
          <Typography variant="body2" sx={{ color: '#718096' }}>
            No recent activity to display. Activity will appear here as employees check in and out.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
