import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  MenuItem,
  Chip,
  Grid,
  Card,
  CardContent,
  InputAdornment,
} from '@mui/material';
import { Search as SearchIcon, CheckCircle, Cancel, AccessTime } from '@mui/icons-material';
import { attendanceAPI } from '../services/api';

interface AttendanceRecord {
  id: string;
  employee_name: string;
  employee_code: string;
  date: string;
  check_in: string;
  check_out: string | null;
  status: string;
  total_hours: number | null;
}

export default function Attendance() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: attendanceData, isLoading } = useQuery({
    queryKey: ['attendance'],
    queryFn: () => attendanceAPI.getAll().then((res) => res.data),
    refetchInterval: 10000,
  });

  const records = attendanceData?.attendance || [];
  const filtered = records.filter((r: AttendanceRecord) => {
    const matchSearch = r.employee_name?.toLowerCase().includes(search.toLowerCase()) ||
      r.employee_code?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || r.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'PRESENT': return { icon: <CheckCircle sx={{ fontSize: 14 }} />, bg: '#f0fff4', color: '#2f855a' };
      case 'ABSENT': return { icon: <Cancel sx={{ fontSize: 14 }} />, bg: '#fff5f5', color: '#c53030' };
      case 'LATE': return { icon: <AccessTime sx={{ fontSize: 14 }} />, bg: '#fffaf0', color: '#c05621' };
      case 'HALF_DAY': return { icon: <AccessTime sx={{ fontSize: 14 }} />, bg: '#fffff0', color: '#975a16' };
      default: return { icon: null, bg: '#f7fafc', color: '#4a5568' };
    }
  };

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Attendance</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          {records.length} total attendance records
        </Typography>
      </Box>

      <Card sx={{ mb: 2.5 }}>
        <CardContent sx={{ py: 2, px: 2.5 }}>
          <Grid container spacing={2} sx={{ alignItems: 'center' }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                size="small"
                placeholder="Search by name or code..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                fullWidth
                slotProps={{ input: {
                  startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#a0aec0' }} /></InputAdornment>,
                } }}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                size="small"
                select
                fullWidth
                label="Status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All Status</MenuItem>
                <MenuItem value="PRESENT">Present</MenuItem>
                <MenuItem value="ABSENT">Absent</MenuItem>
                <MenuItem value="LATE">Late</MenuItem>
                <MenuItem value="HALF_DAY">Half Day</MenuItem>
              </TextField>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Code</TableCell>
              <TableCell>Employee</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Hours</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((record: AttendanceRecord) => {
              const st = getStatusConfig(record.status);
              return (
                <TableRow key={record.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                      {record.employee_code}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {record.employee_name}
                    </Typography>
                  </TableCell>
                  <TableCell>{record.date}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {record.check_in ? new Date(record.check_in).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ color: record.check_out ? 'inherit' : '#a0aec0' }}>
                      {record.check_out ? new Date(record.check_out).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {record.total_hours ? `${record.total_hours.toFixed(1)}h` : '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={st.icon ?? undefined}
                      label={record.status}
                      size="small"
                      sx={{
                        backgroundColor: st.bg,
                        color: st.color,
                        fontWeight: 600,
                        fontSize: '0.7rem',
                      }}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
