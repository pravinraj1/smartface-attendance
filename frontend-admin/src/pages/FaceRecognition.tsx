import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  MenuItem,
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  PersonSearch as PersonSearchIcon,
} from '@mui/icons-material';
import { attendanceAPI, employeeAPI } from '../services/api';

interface AttendanceLog {
  id: string;
  employee_id: string;
  event_type: string;
  confidence_score: number;
  snapshot_url: string;
  created_at: string;
  status: string;
}

interface Employee {
  id: string;
  full_name: string;
  employee_code: string;
}

const eventTypes = [
  { value: '', label: 'All Events' },
  { value: 'CHECK_IN', label: 'Check In' },
  { value: 'CHECK_OUT', label: 'Check Out' },
  { value: 'UNKNOWN_FACE', label: 'Unknown Face' },
  { value: 'FAILED_RECOGNITION', label: 'Failed Recognition' },
];

export default function FaceRecognition() {
  const [employeeFilter, setEmployeeFilter] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['attendanceLogs', employeeFilter, eventTypeFilter],
    queryFn: () =>
      attendanceAPI
        .getLogs({
          employee_id: employeeFilter || undefined,
          event_type: eventTypeFilter || undefined,
          limit: 100,
        })
        .then((res) => res.data),
    refetchInterval: 30000,
  });

  const { data: employeesData } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll({ limit: 200 }).then((res) => res.data),
  });

  const { data: statsData } = useQuery({
    queryKey: ['attendanceStats'],
    queryFn: () => attendanceAPI.getStats().then((res) => res.data),
    refetchInterval: 30000,
  });

  const logs: AttendanceLog[] = logsData?.logs || logsData || [];
  const employees: Employee[] = employeesData?.employees || [];

  const unknownFaceCount = logs.filter(
    (l) => l.event_type === 'UNKNOWN_FACE' || l.event_type === 'FAILED_RECOGNITION'
  ).length;

  const checkInCount = logs.filter((l) => l.event_type === 'CHECK_IN').length;
  const checkOutCount = logs.filter((l) => l.event_type === 'CHECK_OUT').length;

  const getEmployeeName = (employeeId: string) => {
    const emp = employees.find((e) => e.id === employeeId);
    return emp?.full_name || 'Unknown';
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getConfidenceColor = (score: number) => {
    if (score > 0.9) return 'success';
    if (score > 0.7) return 'warning';
    return 'error';
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'CHECK_IN':
        return 'success';
      case 'CHECK_OUT':
        return 'info';
      case 'UNKNOWN_FACE':
        return 'warning';
      case 'FAILED_RECOGNITION':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    if (status === 'SUCCESS') return <CheckIcon sx={{ fontSize: 16, color: 'success.main' }} />;
    return <CancelIcon sx={{ fontSize: 16, color: 'error.main' }} />;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <VisibilityIcon sx={{ mr: 1 }} />
        <Typography variant="h4">Face Recognition Monitor</Typography>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CheckIcon sx={{ fontSize: 40, color: 'success.main', mr: 2 }} />
                <Box>
                  <Typography variant="h4">{statsData?.total_check_ins || checkInCount}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Check Ins Today
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CancelIcon sx={{ fontSize: 40, color: 'info.main', mr: 2 }} />
                <Box>
                  <Typography variant="h4">{statsData?.total_check_outs || checkOutCount}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Check Outs Today
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <WarningIcon sx={{ fontSize: 40, color: 'warning.main', mr: 2 }} />
                <Box>
                  <Typography variant="h4">{unknownFaceCount}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Unknown Faces
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <PersonSearchIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
                <Box>
                  <Typography variant="h4">{statsData?.total_employees || employees.length}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Employees
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Filter by Employee"
          size="small"
          select
          sx={{ minWidth: 200 }}
          value={employeeFilter}
          onChange={(e) => setEmployeeFilter(e.target.value)}
        >
          <MenuItem value="">All Employees</MenuItem>
          {employees.map((emp) => (
            <MenuItem key={emp.id} value={emp.id}>
              {emp.full_name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Event Type"
          size="small"
          select
          sx={{ minWidth: 200 }}
          value={eventTypeFilter}
          onChange={(e) => setEventTypeFilter(e.target.value)}
        >
          {eventTypes.map((et) => (
            <MenuItem key={et.value} value={et.value}>
              {et.label}
            </MenuItem>
          ))}
        </TextField>
        <Chip
          label="Auto-refresh: 30s"
          size="small"
          variant="outlined"
          sx={{ alignSelf: 'center' }}
        />
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>Employee</TableCell>
              <TableCell>Event Type</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No recognition events found
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{formatTime(log.created_at)}</TableCell>
                  <TableCell>{getEmployeeName(log.employee_id)}</TableCell>
                  <TableCell>
                    <Chip
                      label={log.event_type?.replace('_', ' ')}
                      color={getEventColor(log.event_type) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={`${(log.confidence_score * 100).toFixed(1)}%`}
                      color={getConfidenceColor(log.confidence_score) as any}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getStatusIcon(log.status)}
                      <Typography variant="body2">{log.status}</Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
