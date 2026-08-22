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
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      handleClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      employeeAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      handleClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => employeeAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
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
      setFormData({
        employee_code: '',
        full_name: '',
        mobile_number: '',
        department_id: '',
        monthly_salary: '',
        employment_status: 'ACTIVE',
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setSelectedEmployee(null);
  };

  const handleSubmit = () => {
    const data = {
      ...formData,
      monthly_salary: formData.monthly_salary ? parseFloat(formData.monthly_salary) : null,
    };
    
    if (selectedEmployee) {
      updateMutation.mutate({ id: selectedEmployee.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this employee?')) {
      deleteMutation.mutate(id);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'success';
      case 'INACTIVE':
        return 'error';
      case 'SUSPENDED':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Employees</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
        >
          Add Employee
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Code</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Mobile</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Face Enrolled</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {employeesData?.employees?.map((emp: Employee) => (
              <TableRow key={emp.id}>
                <TableCell>{emp.employee_code}</TableCell>
                <TableCell>{emp.full_name}</TableCell>
                <TableCell>{emp.mobile_number}</TableCell>
                <TableCell>
                  {departments?.find((d: Department) => d.id === emp.department_id)?.name || '-'}
                </TableCell>
                <TableCell>
                  <Chip
                    label={emp.employment_status}
                    color={getStatusColor(emp.employment_status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={emp.face_enrolled ? 'Yes' : 'No'}
                    color={emp.face_enrolled ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  <IconButton onClick={() => handleOpen(emp)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(emp.id)}>
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedEmployee ? 'Edit Employee' : 'Add Employee'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Employee Code"
            fullWidth
            value={formData.employee_code}
            onChange={(e) => setFormData({ ...formData, employee_code: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Full Name"
            fullWidth
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Mobile Number"
            fullWidth
            value={formData.mobile_number}
            onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Department"
            fullWidth
            select
            value={formData.department_id}
            onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
          >
            {departments?.map((dept: Department) => (
              <MenuItem key={dept.id} value={dept.id}>
                {dept.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            margin="dense"
            label="Monthly Salary"
            fullWidth
            type="number"
            value={formData.monthly_salary}
            onChange={(e) => setFormData({ ...formData, monthly_salary: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Employment Status"
            fullWidth
            select
            value={formData.employment_status}
            onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}
          >
            <MenuItem value="ACTIVE">Active</MenuItem>
            <MenuItem value="INACTIVE">Inactive</MenuItem>
            <MenuItem value="TERMINATED">Terminated</MenuItem>
            <MenuItem value="SUSPENDED">Suspended</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {selectedEmployee ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
