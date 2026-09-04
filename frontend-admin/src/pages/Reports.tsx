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
  MenuItem,
  Alert,
} from '@mui/material';
import {
  Assessment as AssessmentIcon, People as PeopleIcon, AccessTime as AccessTimeIcon,
  Download as DownloadIcon, PictureAsPdf as PdfIcon,
} from '@mui/icons-material';
import { reportsAPI, employeeAPI, departmentAPI } from '../services/api';

type Period = '' | 'day' | 'week' | 'month';

// Compute the auto date range for the chosen period (same logic as backend IST).
function periodRange(period: Period): { start_date?: string; end_date?: string } {
  if (!period) return {};
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const d = now.getDate();
  const iso = (dt: Date) => dt.toISOString().slice(0, 10);
  if (period === 'day') {
    const dt = new Date(y, m, d);
    return { start_date: iso(dt), end_date: iso(dt) };
  }
  if (period === 'week') {
    const dow = (now.getDay() + 6) % 7; // Monday=0
    const start = new Date(y, m, d - dow);
    const end = new Date(y, m, d - dow + 6);
    return { start_date: iso(start), end_date: iso(end) };
  }
  // month
  const start = new Date(y, m, 1);
  const end = new Date(y, m + 1, 0);
  return { start_date: iso(start), end_date: iso(end) };
}

function fmtMinutes(minutes?: number): string {
  const m = minutes || 0;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? `${h}h ${rem}m` : `${h}h`;
}

const PERIOD_LABELS: { value: Period; label: string }[] = [
  { value: '', label: 'Custom Range' },
  { value: 'day', label: 'Daily' },
  { value: 'week', label: 'Weekly' },
  { value: 'month', label: 'Monthly' },
];

export default function Reports() {
  const [period, setPeriod] = useState<Period>('week');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [notify, setNotify] = useState('');

  const autoRange = periodRange(period);
  const effStart = period ? autoRange.start_date : (startDate || undefined);
  const effEnd = period ? autoRange.end_date : (endDate || undefined);

  const { data: employeesData } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll().then((res) => res.data),
  });
  const employeeList = employeesData?.employees;
  const employees = Array.isArray(employeeList) ? employeeList : [];

  const { data: departmentsData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentAPI.getAll().then((res) => res.data),
  });
  const departments = Array.isArray(departmentsData) ? departmentsData : [];

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['reportSummary', period, startDate, endDate, departmentId, employeeId],
    queryFn: () => reportsAPI.getSummary({
      period: period || undefined,
      start_date: effStart,
      end_date: effEnd,
      department_id: departmentId || undefined,
      employee_id: employeeId || undefined,
    }).then((res) => res.data),
  });

  const selectedEmployee = employeeId ? employees.find((e: any) => e.id === employeeId) : null;
  const deptSummary = Array.isArray(summary?.department_summary) ? summary!.department_summary : [];

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExport = async (format: 'csv' | 'pdf') => {
    try {
      const params = {
        period: period || undefined,
        start_date: effStart,
        end_date: effEnd,
        department_id: departmentId || undefined,
        employee_id: employeeId || undefined,
      };
      const suffix = `${period || 'custom'}_${period ? '' : (effStart || 'all')}_${period ? '' : (effEnd || 'all')}`;
      if (format === 'pdf') {
        if (selectedEmployee) {
          const res = await reportsAPI.exportEmployeePdf(selectedEmployee.id, {
            period: period || undefined,
            start_date: effStart,
            end_date: effEnd,
          });
          downloadBlob(new Blob([res.data], { type: 'application/pdf' }), `employee_report_${selectedEmployee.employee_code}.pdf`);
        } else {
          const res = await reportsAPI.exportSummaryPdf(params);
          downloadBlob(new Blob([res.data], { type: 'application/pdf' }), `attendance_summary_${suffix}.pdf`);
        }
      } else {
        const res = await reportsAPI.exportSummary(params);
        downloadBlob(new Blob([res.data], { type: 'text/csv' }), `attendance_summary_${suffix}.csv`);
      }
      setNotify(`${format.toUpperCase()} downloaded`);
      setTimeout(() => setNotify(''), 2500);
    } catch (e) {
      setNotify('Export failed. Please try again.');
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Reports</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Daily, weekly and monthly attendance analytics &amp; reporting
        </Typography>
      </Box>

      {notify && <Alert severity="info" sx={{ mb: 2, borderRadius: 1 }}>{notify}</Alert>}

      {/* Filters */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent sx={{ py: 2.5 }}>
          <Grid container spacing={2} sx={{ alignItems: 'center' }}>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                select
                size="small"
                label="Period"
                fullWidth
                value={period}
                onChange={(e) => setPeriod(e.target.value as Period)}
              >
                {PERIOD_LABELS.map((p) => (
                  <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                size="small"
                type="date"
                label="Start Date"
                fullWidth
                value={period ? autoRange.start_date || '' : startDate}
                disabled={!!period}
                onChange={(e) => setStartDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                size="small"
                type="date"
                label="End Date"
                fullWidth
                value={period ? autoRange.end_date || '' : endDate}
                disabled={!!period}
                onChange={(e) => setEndDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                select
                size="small"
                label="Employee"
                fullWidth
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
              >
                <MenuItem value="">All Employees</MenuItem>
                {employees.map((e: any) => (
                  <MenuItem key={e.id} value={e.id}>{e.employee_code} - {e.full_name}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                select
                size="small"
                label="Department"
                fullWidth
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
              >
                <MenuItem value="">All Departments</MenuItem>
                {departments.map((d: any) => (
                  <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 2 }} sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" sx={{ py: 1.05, flex: 1 }} startIcon={<PdfIcon />}
                onClick={() => handleExport('pdf')}>
                PDF
              </Button>
              <Button variant="outlined" sx={{ py: 1.05, flex: 1 }} startIcon={<DownloadIcon />}
                onClick={() => handleExport('csv')}>
                CSV
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ width: 48, height: 48, borderRadius: '12px', backgroundColor: '#ebf4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2b6cb0' }}>
                <AssessmentIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Total Working Days
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>{summary?.total_working_days || 0}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ width: 48, height: 48, borderRadius: '12px', backgroundColor: '#f0fff4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2f855a' }}>
                <PeopleIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Present / Employees
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {summary?.present_days || 0} / {summary?.total_employees || 0}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ width: 48, height: 48, borderRadius: '12px', backgroundColor: '#fffaf0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#c05621' }}>
                <AccessTimeIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Total Absences
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>{summary?.total_absences || 0}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Employee / Department Breakdown */}
      {selectedEmployee ? (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Employee Report — {selectedEmployee.full_name} ({selectedEmployee.employee_code})</Typography>
            <Typography variant="body2" sx={{ color: '#718096', mb: 2 }}>
              {summary?.present_days || 0} present / {summary?.total_absences || 0} absent / {summary?.late_days || 0} late · {((summary?.avg_attendance_rate || 0) * 100).toFixed(1)}%
            </Typography>
            <Typography variant="body2" sx={{ color: '#2f855a', fontWeight: 600, mb: 2 }}>
              Total: {fmtMinutes(summary?.total_work_minutes)} · Normal: {fmtMinutes(summary?.total_normal_minutes)} · OT: {fmtMinutes(summary?.total_overtime_minutes)}
            </Typography>
            <Button
              variant="contained"
              startIcon={<PdfIcon />}
              onClick={() => handleExport('pdf')}
            >
              Download Employee PDF
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Department Breakdown</Typography>
            {deptSummary.length > 0 ? (
              deptSummary.map((dept: any) => (
                <Box key={dept.department_id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1.5, borderBottom: '1px solid #edf2f7', '&:last-child': { borderBottom: 'none' } }}>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{dept.department_name}</Typography>
                    <Typography variant="caption" sx={{ color: '#718096' }}>
                      {dept.present_days} present / {dept.absent_days} absent / {dept.late_days} late · Work: {fmtMinutes(dept.total_work_minutes)} · OT: {fmtMinutes(dept.total_overtime_minutes)}
                    </Typography>
                  </Box>
                  <Chip label={`${dept.total_employees} employees`} size="small" sx={{ backgroundColor: '#ebf4ff', color: '#2b6cb0', fontWeight: 600, fontSize: '0.7rem' }} />
                </Box>
              ))
            ) : (
              <Typography variant="body2" sx={{ color: '#a0aec0', py: 2 }}>
                No department data available. Set a period/date and refresh.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
