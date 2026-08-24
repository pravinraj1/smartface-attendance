import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Grid,
  Button,
} from '@mui/material';
import { Search as SearchIcon, Visibility as VisibilityIcon } from '@mui/icons-material';
import { faceAPI } from '../services/api';

interface RecognitionLog {
  id: string;
  employee_name: string;
  employee_code: string;
  confidence: number;
  recognized_at: string;
  recognition_method: string;
}

export default function FaceRecognition() {
  const [limit, setLimit] = useState(50);

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['faceRecognitionLogs', limit],
    queryFn: () => faceAPI.getRecognitionLogs(limit).then((res) => res.data),
  });

  const logs = logsData?.logs || [];

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Face Recognition</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Monitor face recognition activity across the system
        </Typography>
      </Box>

      {/* Stats */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{
                width: 48, height: 48, borderRadius: '12px', backgroundColor: '#ebf4ff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2b6cb0',
              }}>
                <VisibilityIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Total Recognitions
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {logs.length}
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
                <VisibilityIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Avg Confidence
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {logs.length > 0
                    ? `${(logs.reduce((sum: number, l: RecognitionLog) => sum + l.confidence, 0) / logs.length * 100).toFixed(1)}%`
                    : '0%'}
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
                <VisibilityIcon />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Today's Recognitions
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {logs.filter((l: RecognitionLog) => {
                    const today = new Date().toISOString().split('T')[0];
                    return l.recognized_at?.startsWith(today);
                  }).length}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Logs Table */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Recognition Logs</Typography>
            <TextField
              size="small"
              select
              label="Show"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              sx={{ width: 100 }}
            >
              <MenuItem value={25}>25</MenuItem>
              <MenuItem value={50}>50</MenuItem>
              <MenuItem value={100}>100</MenuItem>
            </TextField>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Employee</TableCell>
                  <TableCell>Code</TableCell>
                  <TableCell>Confidence</TableCell>
                  <TableCell>Method</TableCell>
                  <TableCell>Time</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" sx={{ color: '#a0aec0', textAlign: 'center', py: 4 }}>
                        No recognition logs yet
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log: RecognitionLog) => (
                    <TableRow key={log.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {log.employee_name || 'Unknown'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                          {log.employee_code || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={`${(log.confidence * 100).toFixed(1)}%`}
                          size="small"
                          sx={{
                            backgroundColor: log.confidence >= 0.7 ? '#f0fff4' : log.confidence >= 0.4 ? '#fffaf0' : '#fff5f5',
                            color: log.confidence >= 0.7 ? '#2f855a' : log.confidence >= 0.4 ? '#c05621' : '#c53030',
                            fontWeight: 600,
                            fontSize: '0.7rem',
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.recognition_method || 'kiosk'}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: '#718096' }}>
                          {log.recognized_at
                            ? new Date(log.recognized_at).toLocaleString('en-US', {
                              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true,
                            })
                            : '-'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
