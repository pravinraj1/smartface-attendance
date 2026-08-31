import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
  InputAdornment,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon, Search as SearchIcon } from '@mui/icons-material';
import { employeeAPI, departmentAPI } from '../services/api';

interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  mobile_number: string;
  department_id: string;
  monthly_salary: number;
  employment_status: string;
  face_enrolled: boolean;
}

interface Department {
  id: string;
  name: string;
}

export default function Employees() {
  const [open, setOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [search, setSearch] = useState('');
  const [formData, setFormData] = useState({
    employee_code: '',
    full_name: '',
    mobile_number: '',
    department_id: '',
    monthly_salary: '',
    employment_status: 'ACTIVE',
  });
  const queryClient = useQueryClient();

  const { data: employeesData, isLoading } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll().then((res) => res.data),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentAPI.getAll().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => employeeAPI.create(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['employees'] }); handleClose(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => employeeAPI.update(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['employees'] }); handleClose(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => employeeAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  });

  const handleOpen = (employee?: Employee) => {
    if (employee) {
      setSelectedEmployee(employee);
      setFormData({
        employee_code: employee.employee_code,
        full_name: employee.full_name,
        mobile_number: employee.mobile_number || '',
        department_id: employee.department_id || '',
        monthly_salary: employee.monthly_salary?.toString() || '',
        employment_status: employee.employment_status,
      });
    } else {
      setSelectedEmployee(null);
      setFormData({ employee_code: '', full_name: '', mobile_number: '', department_id: '', monthly_salary: '', employment_status: 'ACTIVE' });
    }
    setOpen(true);
  };

  const handleClose = () => { setOpen(false); setSelectedEmployee(null); };

  const handleSubmit = () => {
    const data = { ...formData, monthly_salary: formData.monthly_salary ? parseFloat(formData.monthly_salary) : null };
    if (selectedEmployee) { updateMutation.mutate({ id: selectedEmployee.id, data }); }
    else { createMutation.mutate(data); }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this employee?')) {
      deleteMutation.mutate(id);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return { bg: '#f0fff4', color: '#2f855a' };
      case 'INACTIVE': return { bg: '#fff5f5', color: '#c53030' };
      case 'SUSPENDED': return { bg: '#fffaf0', color: '#c05621' };
      default: return { bg: '#f7fafc', color: '#4a5568' };
    }
  };

  const employees = employeesData?.employees || [];
  const filtered = employees.filter((e: Employee) =>
    e.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    e.employee_code?.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Employees</Typography>
          <Typography variant="body2" sx={{ color: '#718096' }}>{employees.length} total employees</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
          Add Employee
        </Button>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1.5, px: 2 }}>
          <TextField
            size="small"
            placeholder="Search employees..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{ input: {
              startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#a0aec0' }} /></InputAdornment>,
            } }}
            sx={{ width: 300 }}
          />
        </CardContent>
      </Card>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Code</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Mobile</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Face</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((emp: Employee) => {
              const st = getStatusColor(emp.employment_status);
              return (
                <TableRow key={emp.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                      {emp.employee_code}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>{emp.full_name}</Typography>
                  </TableCell>
                  <TableCell>{emp.mobile_number || '-'}</TableCell>
                  <TableCell>
                    {departments?.find((d: Department) => d.id === emp.department_id)?.name || '-'}
                  </TableCell>
                  <TableCell>
                    <Chip label={emp.employment_status} size="small" sx={{ backgroundColor: st.bg, color: st.color, fontWeight: 600, fontSize: '0.7rem' }} />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={emp.face_enrolled ? 'Enrolled' : 'Not Enrolled'}
                      size="small"
                      sx={{
                        backgroundColor: emp.face_enrolled ? '#f0fff4' : '#f7fafc',
                        color: emp.face_enrolled ? '#2f855a' : '#a0aec0',
                        fontWeight: 600,
                        fontSize: '0.7rem',
                      }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => handleOpen(emp)}><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" onClick={() => handleDelete(emp.id)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>{selectedEmployee ? 'Edit Employee' : 'Add Employee'}</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Employee Code" fullWidth size="small" value={formData.employee_code} onChange={(e) => setFormData({ ...formData, employee_code: e.target.value })} />
          <TextField margin="dense" label="Full Name" fullWidth size="small" value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} />
          <TextField margin="dense" label="Mobile Number" fullWidth size="small" value={formData.mobile_number} onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })} />
          <TextField margin="dense" label="Department" fullWidth size="small" select value={formData.department_id} onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}>
            {departments?.map((dept: Department) => (<MenuItem key={dept.id} value={dept.id}>{dept.name}</MenuItem>))}
          </TextField>
          <TextField margin="dense" label="Monthly Salary" fullWidth size="small" type="number" value={formData.monthly_salary} onChange={(e) => setFormData({ ...formData, monthly_salary: e.target.value })} />
          <TextField margin="dense" label="Employment Status" fullWidth size="small" select value={formData.employment_status} onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}>
            <MenuItem value="ACTIVE">Active</MenuItem>
            <MenuItem value="INACTIVE">Inactive</MenuItem>
            <MenuItem value="TERMINATED">Terminated</MenuItem>
            <MenuItem value="SUSPENDED">Suspended</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} variant="outlined" size="small">Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" size="small">{selectedEmployee ? 'Update' : 'Create'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

