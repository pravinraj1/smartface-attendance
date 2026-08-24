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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { departmentAPI } from '../services/api';

interface Department {
  id: string;
  name: string;
  employee_count: number;
}

export default function Departments() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Department | null>(null);
  const [name, setName] = useState('');
  const queryClient = useQueryClient();

  const { data: departments, isLoading } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentAPI.getAll().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string }) => departmentAPI.create(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['departments'] }); handleClose(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name: string } }) => departmentAPI.update(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['departments'] }); handleClose(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => departmentAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  });

  const handleOpen = (dept?: Department) => {
    if (dept) {
      setSelected(dept);
      setName(dept.name);
    } else {
      setSelected(null);
      setName('');
    }
    setOpen(true);
  };

  const handleClose = () => { setOpen(false); setSelected(null); setName(''); };

  const handleSubmit = () => {
    if (!name.trim()) return;
    if (selected) { updateMutation.mutate({ id: selected.id, data: { name } }); }
    else { createMutation.mutate({ name }); }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure? This will fail if employees are assigned to this department.')) {
      deleteMutation.mutate(id);
    }
  };

  if (isLoading) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Departments</Typography>
          <Typography variant="body2" sx={{ color: '#718096' }}>{departments?.length || 0} departments</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
          Add Department
        </Button>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Department Name</TableCell>
              <TableCell>Employees</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {departments?.map((dept: Department) => (
              <TableRow key={dept.id} hover>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{dept.name}</Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={`${dept.employee_count || 0} employees`}
                    size="small"
                    sx={{
                      backgroundColor: '#ebf4ff',
                      color: '#2b6cb0',
                      fontWeight: 600,
                      fontSize: '0.7rem',
                    }}
                  />
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => handleOpen(dept)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(dept.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>
          {selected ? 'Edit Department' : 'Add Department'}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Department Name"
            fullWidth
            size="small"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} variant="outlined" size="small">Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" size="small">
            {selected ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
