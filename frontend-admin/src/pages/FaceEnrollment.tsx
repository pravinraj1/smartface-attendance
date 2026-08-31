import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  TextField,
  MenuItem,
  Alert,
  Grid,
  Paper,
} from '@mui/material';
import { Face as FaceIcon, CameraAlt as CameraIcon, Check as CheckIcon } from '@mui/icons-material';
import { employeeAPI, faceAPI } from '../services/api';

interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  face_enrolled: boolean;
}

const steps = ['Select Employee', 'Capture Face', 'Confirm Enrollment'];

export default function FaceEnrollment() {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState('');
  const queryClient = useQueryClient();

  const { data: employeesData } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll().then((res) => res.data),
  });

  const employees = (employeesData?.employees || []).filter((e: Employee) => !e.face_enrolled);

  const handleCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setCapturedImage(reader.result as string);
      reader.readAsDataURL(file);
    }
  };

  const handleNext = async () => {
    setError('');
    setDuplicateWarning('');

    if (activeStep === 0) {
      if (!selectedEmployeeId) { setError('Please select an employee'); return; }
      // Check for duplicate face
      if (capturedImage) {
        try {
          const resp = await fetch('/api/v1/faces/check-duplicate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
            body: JSON.stringify({
              image: capturedImage,
              exclude_employee_id: selectedEmployeeId,
            }),
          });
          const data = await resp.json();
          if (data.is_duplicate) {
            setDuplicateWarning(`This face is already enrolled for: ${data.existing_employee_name} (${data.existing_employee_code}). Cannot enroll the same face for multiple employees.`);
            return;
          }
        } catch (err) { /* proceed if check fails */ }
      }
      setActiveStep(1);
    } else if (activeStep === 1) {
      if (!capturedImage) { setError('Please capture a photo'); return; }
      // Check duplicate again before enrollment
      try {
        const resp = await fetch('/api/v1/faces/check-duplicate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify({
            image: capturedImage,
            exclude_employee_id: selectedEmployeeId,
          }),
        });
        const data = await resp.json();
        if (data.is_duplicate) {
          setDuplicateWarning(`This face is already enrolled for: ${data.existing_employee_name} (${data.existing_employee_code}).`);
          return;
        }
      } catch (err) { /* proceed */ }
      setActiveStep(2);
    }
  };

  const handleEnroll = async () => {
    setError('');
    try {
      await faceAPI.enroll(selectedEmployeeId, capturedImage!);
      setSuccess('Face enrolled successfully!');
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      setTimeout(() => {
        setActiveStep(0);
        setSelectedEmployeeId('');
        setCapturedImage(null);
        setSuccess('');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Enrollment failed');
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Face Enrollment</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Register employee faces for biometric attendance
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 1 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2, borderRadius: 1 }}>{success}</Alert>}
      {duplicateWarning && <Alert severity="warning" sx={{ mb: 2, borderRadius: 1 }}>{duplicateWarning}</Alert>}

      <Card>
        <CardContent sx={{ p: 3 }}>
          {activeStep === 0 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Select Employee</Typography>
              <TextField
                select
                fullWidth
                label="Choose an employee to enroll"
                value={selectedEmployeeId}
                onChange={(e) => setSelectedEmployeeId(e.target.value)}
                size="small"
              >
                {employees.map((emp: Employee) => (
                  <MenuItem key={emp.id} value={emp.id}>
                    {emp.employee_code} - {emp.full_name}
                  </MenuItem>
                ))}
              </TextField>
              {employees.length === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  All employees have been enrolled, or no employees exist yet.
                </Alert>
              )}
            </Box>
          )}

          {activeStep === 1 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Capture Face Photo</Typography>
              <Grid container spacing={2} sx={{ alignItems: 'center' }}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper
                    sx={{
                      height: 300,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f7fafc',
                      border: '2px dashed #e2e8f0',
                      borderRadius: 2,
                    }}
                  >
                    {capturedImage ? (
                      <img src={capturedImage} alt="Captured" style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 8 }} />
                    ) : (
                      <>
                        <CameraIcon sx={{ fontSize: 48, color: '#cbd5e0', mb: 1 }} />
                        <Typography variant="body2" sx={{ color: '#a0aec0' }}>
                          Take a clear, front-facing photo
                        </Typography>
                      </>
                    )}
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Button variant="contained" component="label" startIcon={<CameraIcon />}>
                    {capturedImage ? 'Retake Photo' : 'Take Photo'}
                    <input type="file" accept="image/*" capture="user" hidden onChange={handleCapture} />
                  </Button>
                  <Alert severity="info" sx={{ mt: 2 }}>
                    Use a clear, well-lit photo. Face should be centered and looking at the camera.
                  </Alert>
                </Grid>
              </Grid>
            </Box>
          )}

          {activeStep === 2 && (
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Confirm Enrollment</Typography>
              {capturedImage && (
                <Box sx={{ mb: 2 }}>
                  <img src={capturedImage} alt="To enroll" style={{ maxWidth: 300, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                </Box>
              )}
              <Typography variant="body2" sx={{ color: '#718096', mb: 2 }}>
                Ready to enroll this face for the selected employee.
              </Typography>
              <Button variant="contained" startIcon={<CheckIcon />} onClick={handleEnroll} size="large">
                Confirm & Enroll
              </Button>
            </Box>
          )}

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
            {activeStep > 0 && activeStep < 2 && (
              <Button onClick={() => setActiveStep(activeStep - 1)} sx={{ mr: 1 }}>
                Back
              </Button>
            )}
            {activeStep < 2 && (
              <Button variant="contained" onClick={handleNext} disabled={activeStep === 0 && !selectedEmployeeId}>
                Next
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
