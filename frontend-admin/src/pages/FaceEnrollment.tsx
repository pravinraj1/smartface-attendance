import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Grid,
  Paper,
  TextField,
  MenuItem,
  Chip,
  Button,
  IconButton,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  Alert,
  CircularProgress,
  Divider,
  Avatar,
  Stack,
} from '@mui/material';
import {
  Face as FaceIcon,
  Delete as DeleteIcon,
  CloudUpload as UploadIcon,
  CameraAlt as CameraIcon,
  CheckCircle as CheckIcon,
  ArrowBack as BackIcon,
  ArrowForward as NextIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { employeeAPI, faceAPI } from '../services/api';
import CameraCapture from '../components/CameraCapture';

interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  face_enrolled: boolean;
  department_id: string;
}

interface FaceProfile {
  id: string;
  employee_id: string;
  face_image_url: string;
  created_at: string;
  is_primary: boolean;
}

const steps = ['Select Employee', 'Capture Face', 'Preview', 'Done'];

export default function FaceEnrollment() {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [capturedPreview, setCapturedPreview] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState<string>('');
  const [duplicateChecking, setDuplicateChecking] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: employeesData, isLoading: employeesLoading } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeAPI.getAll({ limit: 200 }).then((res) => res.data),
  });

  const { data: faceProfiles, isLoading: facesLoading } = useQuery({
    queryKey: ['faceProfiles', selectedEmployeeId],
    queryFn: () => faceAPI.getEmployeeFaces(selectedEmployeeId).then((res) => res.data),
    enabled: !!selectedEmployeeId,
  });

  const enrollMutation = useMutation({
    mutationFn: ({ employeeId, file }: { employeeId: string; file: File }) =>
      faceAPI.enroll(employeeId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faceProfiles'] });
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      setActiveStep(3);
      setSuccessMessage('Face enrolled successfully!');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (faceId: string) => faceAPI.delete(faceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faceProfiles'] });
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });

  const employees: Employee[] = employeesData?.employees || [];
  const enrolledCount = employees.filter((e) => e.face_enrolled).length;
  const totalCount = employees.length;

  const sortedEmployees = [...employees].sort((a, b) => {
    if (a.face_enrolled === b.face_enrolled) return 0;
    return a.face_enrolled ? 1 : -1;
  });

  const selectedEmployee = employees.find((e) => e.id === selectedEmployeeId);

  const checkForDuplicate = async (file: File) => {
    setDuplicateChecking(true);
    setDuplicateWarning('');
    try {
      const res = await faceAPI.checkDuplicate(file, selectedEmployeeId);
      if (res.data.duplicate) {
        setDuplicateWarning(res.data.message);
      }
    } catch {
    } finally {
      setDuplicateChecking(false);
    }
  };

  const handleCapture = (blob: Blob) => {
    const file = new File([blob], `face-${Date.now()}.jpg`, { type: 'image/jpeg' });
    setCapturedFile(file);
    setCapturedPreview(URL.createObjectURL(blob));
    setDuplicateWarning('');
    setActiveStep(2);
    checkForDuplicate(file);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setCapturedFile(file);
      setCapturedPreview(URL.createObjectURL(file));
      setDuplicateWarning('');
      setActiveStep(2);
      checkForDuplicate(file);
    }
  };

  const handleEnroll = () => {
    if (capturedFile && selectedEmployeeId) {
      enrollMutation.mutate({ employeeId: selectedEmployeeId, file: capturedFile });
    }
  };

  const handleRetake = () => {
    setCapturedFile(null);
    setCapturedPreview('');
    setDuplicateWarning('');
    setActiveStep(1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedEmployeeId('');
    setCapturedFile(null);
    setCapturedPreview('');
    setSuccessMessage('');
    setDuplicateWarning('');
  };

  const handleDeleteFace = (faceId: string) => {
    if (window.confirm('Delete this face profile?')) {
      deleteMutation.mutate(faceId);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Face Enrollment</Typography>
        <Chip
          icon={<FaceIcon />}
          label={`${enrolledCount} / ${totalCount} Enrolled`}
          color={enrolledCount === totalCount ? 'success' : 'primary'}
          variant="outlined"
        />
      </Box>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Select Employee
            </Typography>
            <TextField
              select
              fullWidth
              size="small"
              label="Employee"
              value={selectedEmployeeId}
              onChange={(e) => {
                setSelectedEmployeeId(e.target.value);
                if (activeStep === 0) setActiveStep(1);
              }}
              disabled={employeesLoading}
            >
              {sortedEmployees.map((emp) => (
                <MenuItem
                  key={emp.id}
                  value={emp.id}
                  sx={{ opacity: emp.face_enrolled ? 0.5 : 1 }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                    <span>{emp.full_name}</span>
                    {emp.face_enrolled && (
                      <Chip label="Enrolled" size="small" color="success" sx={{ ml: 1 }} />
                    )}
                  </Box>
                </MenuItem>
              ))}
            </TextField>
          </Paper>

          {selectedEmployeeId && (
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Existing Face Profiles
              </Typography>
              {facesLoading ? (
                <CircularProgress size={24} />
              ) : faceProfiles?.length > 0 ? (
                <Grid container spacing={1}>
                  {faceProfiles.map((face: FaceProfile) => (
                    <Grid item xs={4} key={face.id}>
                      <Card variant="outlined" sx={{ position: 'relative' }}>
                        <Avatar
                          src={face.face_image_url}
                          variant="rounded"
                          sx={{ width: '100%', height: 80 }}
                        />
                        <IconButton
                          size="small"
                          sx={{ position: 'absolute', top: 2, right: 2, bgcolor: 'rgba(0,0,0,0.5)' }}
                          onClick={() => handleDeleteFace(face.id)}
                        >
                          <DeleteIcon sx={{ fontSize: 16, color: '#fff' }} />
                        </IconButton>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No face profiles enrolled yet.
                </Typography>
              )}
            </Paper>
          )}

          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <InfoIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="subtitle2">Enrollment Guidelines</Typography>
              </Box>
              <Divider sx={{ mb: 1 }} />
              <Typography variant="body2" color="text.secondary" component="div">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Ensure good lighting</li>
                  <li>Face the camera directly</li>
                  <li>Remove glasses or headwear</li>
                  <li>Keep a neutral expression</li>
                  <li>Ensure face is clearly visible</li>
                </ul>
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, minHeight: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            {activeStep === 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <FaceIcon sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary">
                  Select an employee to begin enrollment
                </Typography>
              </Box>
            )}

            {activeStep === 1 && selectedEmployeeId && (
              <Box sx={{ width: '100%' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Capture face for {selectedEmployee?.full_name}
                  </Typography>
                  <Button startIcon={<UploadIcon />} onClick={() => fileInputRef.current?.click()}>
                    Upload Image
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    hidden
                    onChange={handleFileUpload}
                  />
                </Box>
                <CameraCapture onCapture={handleCapture} />
              </Box>
            )}

            {activeStep === 2 && (
              <Box sx={{ textAlign: 'center', width: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Preview - {selectedEmployee?.full_name}
                </Typography>
                <Box
                  component="img"
                  src={capturedPreview}
                  alt="Captured face"
                  sx={{ maxWidth: '100%', maxHeight: 400, borderRadius: 2, mb: 2 }}
                />
                {duplicateChecking && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Checking if this face is already enrolled...
                  </Alert>
                )}
                {duplicateWarning && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    {duplicateWarning}
                  </Alert>
                )}
                {enrollMutation.isError && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {(enrollMutation.error as any)?.response?.data?.detail || 'Enrollment failed. Ensure the face is clearly visible and try again.'}
                  </Alert>
                )}
                <Stack direction="row" spacing={2} justifyContent="center">
                  <Button variant="outlined" startIcon={<BackIcon />} onClick={handleRetake}>
                    Retake
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={enrollMutation.isPending ? <CircularProgress size={20} /> : <CheckIcon />}
                    onClick={handleEnroll}
                    disabled={enrollMutation.isPending}
                  >
                    Enroll Face
                  </Button>
                </Stack>
              </Box>
            )}

            {activeStep === 3 && (
              <Box sx={{ textAlign: 'center' }}>
                <CheckIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
                <Typography variant="h5" gutterBottom>
                  {successMessage}
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                  Face profile for {selectedEmployee?.full_name} has been enrolled.
                </Typography>
                <Button variant="contained" onClick={handleReset}>
                  Enroll Another Employee
                </Button>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
