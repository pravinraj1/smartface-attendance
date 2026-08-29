import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  Chip,
} from '@mui/material';
import {
  Assessment as AssessmentIcon, People as PeopleIcon, AccessTime as AccessTimeIcon, Download as DownloadIcon,
} from '@mui/icons-material';
import { reportsAPI } from '../services/api';

export default function Reports() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [departmentId, setDepartmentId] = useState('');

  const { data: summary, isLoading: loadingSummary, refetch } = useQuery({
    queryKey: ['reportSummary', startDate, endDate, departmentId],
    queryFn: () => reportsAPI.getSummary({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      department_id: departmentId || undefined,
    }).then((res) => res.data),
  });

  const handleExport = async () => {
    try {
      const res = await reportsAPI.exportSummary({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        department_id: departmentId || undefined,
      });
      const blob = new Blob([res.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_summary_${startDate || 'all'}_${endDate || 'all'}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('Export failed. Please try again.');
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Reports</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Attendance analytics and reporting
        </Typography>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent sx={{ py: 2.5 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={2}>
              <TextField
                size="small"
                type="date"
                label="Start Date"
                fullWidth
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <TextField
                size="small"
                type="date"
                label="End Date"
                fullWidth
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <TextField
                size="small"
                label="Department ID"
                fullWidth
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Button variant="contained" fullWidth sx={{ py: 1.05 }} onClick={() => refetch()}>
                Generate Report
              </Button>
            </Grid>
            <Grid item xs={12} md={3}>
              <Button
                variant="outlined"
                fullWidth
                sx={{ py: 1.05 }}
                startIcon={<DownloadIcon />}
                onClick={handleExport}
              >
                Export CSV
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{
                width: 48, height: 48, borderRadius: '12px', backgroundColor: '#ebf4ff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2b6cb0',
              }}>
                <AssessmentIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Total Working Days
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {summary?.total_working_days || 0}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{
                width: 48, height: 48, borderRadius: '12px', backgroundColor: '#f0fff4',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2f855a',
              }}>
                <PeopleIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Avg Attendance Rate
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {summary?.avg_attendance_rate ? `${(summary.avg_attendance_rate * 100).toFixed(1)}%` : '0%'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{
                width: 48, height: 48, borderRadius: '12px', backgroundColor: '#fffaf0',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#c05621',
              }}>
                <AccessTimeIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Total Absences
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {summary?.total_absences || 0}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Department Breakdown */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Department Breakdown</Typography>
          {summary?.department_summary?.length > 0 ? (
            summary.department_summary.map((dept: any) => (
              <Box
                key={dept.department_id}
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  py: 1.5,
                  borderBottom: '1px solid #edf2f7',
                  '&:last-child': { borderBottom: 'none' },
                }}
              >
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{dept.department_name}</Typography>
                  <Typography variant="caption" sx={{ color: '#718096' }}>
                    {dept.present_days} present / {dept.absent_days} absent / {dept.late_days} late
                  </Typography>
                </Box>
                <Chip
                  label={`${dept.total_employees} employees`}
                  size="small"
                  sx={{ backgroundColor: '#ebf4ff', color: '#2b6cb0', fontWeight: 600, fontSize: '0.7rem' }}
                />
              </Box>
            ))
          ) : (
            <Typography variant="body2" sx={{ color: '#a0aec0', py: 2 }}>
              No department data available. Set a date range and click Generate Report.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
