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
  Paper,
  TextField,
  MenuItem,
  Chip,
} from '@mui/material';
import { attendanceAPI, employeeAPI } from '../services/api';

interface AttendanceRecord {
  id: string;
  employee_id: string;
  attendance_date: string;
  check_in: string;
  check_out: string;
  total_work_minutes: number;
  attendance_status: string;
}

interface Employee {
  id: string;
  full_name: string;
  employee_code: string;
}

export default function Attendance() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [employeeId, setEmployeeId] = useState('');

  const { data: attendance, isLoading } = useQuery({
    queryKey: ['attendance', startDate, endDate, employeeId],
    queryFn: () =>
      attendanceAPI
        .getAll({
          start_date: startDate || undefined,
          end_date: endDate || undefined,
          employee_id: employeeId || undefined,
        })
        .then((res) => res.data),
  });

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll().then((res) => res.data),
  });

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatMinutes = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PRESENT':
        return 'success';
      case 'LATE':
        return 'warning';
      case 'ABSENT':
        return 'error';
      case 'HALF_DAY':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Attendance
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Start Date"
          type="date"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
        <TextField
          label="End Date"
          type="date"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
        <TextField
          label="Employee"
          size="small"
          select
          sx={{ minWidth: 200 }}
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
        >
          <MenuItem value="">All Employees</MenuItem>
          {employees?.employees?.map((emp: Employee) => (
            <MenuItem key={emp.id} value={emp.id}>
              {emp.full_name}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Employee</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Hours</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : attendance?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No attendance records found
                </TableCell>
              </TableRow>
            ) : (
              attendance?.map((record: AttendanceRecord) => {
                const employee = employees?.employees?.find(
                  (e: Employee) => e.id === record.employee_id
                );
                return (
                  <TableRow key={record.id}>
                    <TableCell>{record.attendance_date}</TableCell>
                    <TableCell>{employee?.full_name || '-'}</TableCell>
                    <TableCell>{formatTime(record.check_in)}</TableCell>
                    <TableCell>{formatTime(record.check_out)}</TableCell>
                    <TableCell>{formatMinutes(record.total_work_minutes)}</TableCell>
                    <TableCell>
                      <Chip
                        label={record.attendance_status}
                        color={getStatusColor(record.attendance_status) as any}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
