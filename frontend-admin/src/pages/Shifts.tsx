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
  Chip,
  Switch,
  Alert,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon, AccessTime as AccessTimeIcon } from '@mui/icons-material';
import { shiftsAPI } from '../services/api';

interface Shift {
  id: string;
  shift_name: string;
  start_time: string;
  end_time: string;
  standard_hours: string;
  grace_period: number;
  is_active: boolean;
}

function toHHMM(timeStr?: string): string {
  if (!timeStr) return '';
  return timeStr.slice(0, 5);
}

function isOvernight(start: string, end: string): boolean {
  if (!start || !end) return false;
  return start > end;
}

export default function Shifts() {
  const [open, setOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState<Shift | null>(null);
  const [formData, setFormData] = useState({
    shift_name: '',
    start_time: '09:00',
    end_time: '17:00',
    standard_hours: '8',
    grace_period: '0',
    is_active: true,
  });
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const { data: shiftsData, isLoading } = useQuery({
    queryKey: ['shifts'],
    queryFn: () => shiftsAPI.getAll().then((res) => res.data),
  });
  const shifts = Array.isArray(shiftsData) ? shiftsData : [];

  const createMutation = useMutation({
    mutationFn: (data: any) => shiftsAPI.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shifts'] });
      handleClose();
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Failed to create shift'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => shiftsAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shifts'] });
      handleClose();
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Failed to update shift'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      shiftsAPI.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shifts'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => shiftsAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shifts'] }),
  });

  const handleOpen = (shift?: Shift) => {
    setError('');
    if (shift) {
      setSelectedShift(shift);
      setFormData({
        shift_name: shift.shift_name,
        start_time: toHHMM(shift.start_time),
        end_time: toHHMM(shift.end_time),
        standard_hours: String(Number(shift.standard_hours)),
        grace_period: String(shift.grace_period || 0),
        is_active: shift.is_active,
      });
    } else {
      setSelectedShift(null);
      setFormData({ shift_name: '', start_time: '09:00', end_time: '17:00', standard_hours: '8', grace_period: '0', is_active: true });
    }
    setOpen(true);
  };

  const handleClose = () => { setOpen(false); setSelectedShift(null); setError(''); };

  const handleSubmit = () => {
    setError('');
    if (!formData.shift_name.trim()) { setError('Shift name is required'); return; }
    if (!formData.start_time || !formData.end_time) { setError('Start and end times are required'); return; }
    if (formData.start_time === formData.end_time) { setError('Start and end times must be different'); return; }
    const std = parseFloat(formData.standard_hours);
    if (isNaN(std) || std < 0) { setError('Standard hours must be a non-negative number'); return; }
    const grace = parseInt(formData.grace_period, 10);
    const data = {
      shift_name: formData.shift_name.trim(),
      start_time: `${formData.start_time}:00`,
      end_time: `${formData.end_time}:00`,
      standard_hours: std,
      grace_period: isNaN(grace) ? 0 : grace,
      is_active: formData.is_active,
    };
    if (selectedShift) updateMutation.mutate({ id: selectedShift.id, data });
    else createMutation.mutate(data);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this shift? Employees assigned to it will be unassigned.')) {
      deleteMutation.mutate(id);
    }
  };

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Shift Management</Typography>
          <Typography variant="body2" sx={{ color: '#718096' }}>{shifts.length} shift profiles · assign employees to a shift on the Employees page</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
          Add Shift
        </Button>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Shift Name</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>End</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Std. Hours</TableCell>
              <TableCell>Grace (min)</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {shifts.map((shift: Shift) => (
              <TableRow key={shift.id} hover>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AccessTimeIcon sx={{ color: '#2b6cb0', fontSize: 18 }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{shift.shift_name}</Typography>
                  </Box>
                </TableCell>
                <TableCell>{toHHMM(shift.start_time)}</TableCell>
                <TableCell>{toHHMM(shift.end_time)}</TableCell>
                <TableCell>
                  <Chip
                    label={isOvernight(toHHMM(shift.start_time), toHHMM(shift.end_time)) ? 'Overnight' : 'Day'}
                    size="small"
                    sx={{
                      backgroundColor: isOvernight(toHHMM(shift.start_time), toHHMM(shift.end_time)) ? '#fefcbf' : '#ebf4ff',
                      color: isOvernight(toHHMM(shift.start_time), toHHMM(shift.end_time)) ? '#975a16' : '#2b6cb0',
                      fontWeight: 600, fontSize: '0.7rem',
                    }}
                  />
                </TableCell>
                <TableCell>{Number(shift.standard_hours)}h</TableCell>
                <TableCell>{shift.grace_period || 0}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Switch
                      size="small"
                      checked={shift.is_active}
                      onChange={(e) => toggleMutation.mutate({ id: shift.id, is_active: e.target.checked })}
                      color="success"
                    />
                    <Typography variant="caption" sx={{ color: '#718096' }}>{shift.is_active ? 'Active' : 'Disabled'}</Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => handleOpen(shift)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" onClick={() => handleDelete(shift.id)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {shifts.length === 0 && (
              <TableRow><TableCell colSpan={8} sx={{ textAlign: 'center', color: '#a0aec0', py: 3 }}>No shifts defined yet.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>{selectedShift ? 'Edit Shift' : 'Add Shift'}</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}
          <TextField autoFocus margin="dense" label="Shift Name" fullWidth size="small" value={formData.shift_name} onChange={(e) => setFormData({ ...formData, shift_name: e.target.value })} />
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <TextField margin="dense" label="Start Time" fullWidth size="small" type="time" value={formData.start_time} onChange={(e) => setFormData({ ...formData, start_time: e.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField margin="dense" label="End Time" fullWidth size="small" type="time" value={formData.end_time} onChange={(e) => setFormData({ ...formData, end_time: e.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
          </Box>
          <Typography variant="caption" sx={{ color: isOvernight(formData.start_time, formData.end_time) ? '#975a16' : '#718096' }}>
            {formData.start_time && formData.end_time
              ? (isOvernight(formData.start_time, formData.end_time) ? 'Overnight shift — end time is on the following day.' : 'Day shift.')
              : ''}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <TextField margin="dense" label="Standard Hours" fullWidth size="small" type="number" value={formData.standard_hours} onChange={(e) => setFormData({ ...formData, standard_hours: e.target.value })} />
            <TextField margin="dense" label="Grace Period (min)" fullWidth size="small" type="number" value={formData.grace_period} onChange={(e) => setFormData({ ...formData, grace_period: e.target.value })} />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <Switch checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })} color="success" />
            <Typography variant="body2">Active (available for assignment)</Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} variant="outlined" size="small">Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" size="small">{selectedShift ? 'Update' : 'Create'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
