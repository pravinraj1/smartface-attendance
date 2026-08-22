import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  MenuItem,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { attendanceAPI, employeeAPI } from '../services/api';

interface Employee {
  id: string;
  full_name: string;
  employee_code: string;
}

export default function Reports() {
  const [reportType, setReportType] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [selectedMonth, setSelectedMonth] = useState(
    new Date().toISOString().slice(0, 7)
  );

  const { data: attendance, isLoading } = useQuery({
    queryKey: ['attendance', selectedDate, reportType],
    queryFn: () => {
      if (reportType === 'daily') {
        return attendanceAPI
          .getAll({ start_date: selectedDate, end_date: selectedDate })
          .then((res) => res.data);
      }
      const startDate = `${selectedMonth}-01`;
      const endDate = `${selectedMonth}-31`;
      return attendanceAPI
        .getAll({ start_date: startDate, end_date: endDate })
        .then((res) => res.data);
    },
  });

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll().then((res) => res.data),
  });

  const formatMinutes = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const calculateStats = () => {
    if (!attendance) return { present: 0, absent: 0, late: 0, totalHours: 0 };
    
    const present = attendance.filter(
      (r: any) => r.attendance_status === 'PRESENT' || r.attendance_status === 'LATE'
    ).length;
    const late = attendance.filter(
      (r: any) => r.attendance_status === 'LATE'
    ).length;
    const totalHours = attendance.reduce(
      (sum: number, r: any) => sum + (r.total_work_minutes || 0),
      0
    );
    const totalEmployees = employees?.employees?.length || 0;
    
    return {
      present,
      absent: totalEmployees - present,
      late,
      totalHours: formatMinutes(totalHours),
    };
  };

  const stats = calculateStats();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Reports
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Report Type"
          size="small"
          select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
        >
          <MenuItem value="daily">Daily Report</MenuItem>
          <MenuItem value="monthly">Monthly Report</MenuItem>
        </TextField>

        {reportType === 'daily' ? (
          <TextField
            label="Date"
            type="date"
            size="small"
            InputLabelProps={{ shrink: true }}
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        ) : (
          <TextField
            label="Month"
            type="month"
            size="small"
            InputLabelProps={{ shrink: true }}
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
          />
        )}

        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => alert('Export functionality coming soon')}
        >
          Export PDF
        </Button>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => alert('Export functionality coming soon')}
        >
          Export Excel
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary">Present</Typography>
              <Typography variant="h4">{stats.present}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary">Absent</Typography>
              <Typography variant="h4">{stats.absent}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary">Late</Typography>
              <Typography variant="h4">{stats.late}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary">Total Hours</Typography>
              <Typography variant="h4">{stats.totalHours}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom>
        {reportType === 'daily' ? 'Daily' : 'Monthly'} Report
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee</TableCell>
              <TableCell>Code</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Hours Worked</TableCell>
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
                  No records found
                </TableCell>
              </TableRow>
            ) : (
              attendance?.map((record: any) => {
                const employee = employees?.employees?.find(
                  (e: Employee) => e.id === record.employee_id
                );
                return (
                  <TableRow key={record.id}>
                    <TableCell>{employee?.full_name || '-'}</TableCell>
                    <TableCell>{employee?.employee_code || '-'}</TableCell>
                    <TableCell>{record.attendance_status}</TableCell>
                    <TableCell>
                      {record.check_in
                        ? new Date(record.check_in).toLocaleTimeString()
                        : '-'}
                    </TableCell>
                    <TableCell>
                      {record.check_out
                        ? new Date(record.check_out).toLocaleTimeString()
                        : '-'}
                    </TableCell>
                    <TableCell>{formatMinutes(record.total_work_minutes)}</TableCell>
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
