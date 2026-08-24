import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tabs,
  Tab,
  Chip,
} from '@mui/material';
import {
  Sync as SyncIcon,
  CloudDownload as DownloadIcon,
  Webhook as WebhookIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import api from '../services/api';

interface ERPConfig {
  configured: boolean;
  id?: string;
  erp_name?: string;
  erp_url?: string;
  auth_type?: string;
  data_format?: string;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  last_sync_at?: string;
  last_sync_status?: string;
  webhook_enabled?: boolean;
  endpoint_attendance?: string;
  endpoint_employees?: string;
}

interface SyncLog {
  id: string;
  sync_type: string;
  direction: string;
  status: string;
  records_count: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export default function ERPIntegration() {
  const [tab, setTab] = useState(0);
  const [config, setConfig] = useState<ERPConfig>({ configured: false });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    loadConfig();
    loadSyncLogs();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await api.get('/erp/config');
      if (res.data.configured) {
        setConfig(res.data);
      }
    } catch (e) {
      console.error('Failed to load ERP config');
    } finally {
      setLoading(false);
    }
  };

  const loadSyncLogs = async () => {
    try {
      const res = await api.get('/erp/sync-logs?limit=20');
      setSyncLogs(res.data);
    } catch (e) {
      console.error('Failed to load sync logs');
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const params = new URLSearchParams();
      params.append('erp_name', config.erp_name || 'Custom ERP');
      params.append('erp_url', config.erp_url || '');
      params.append('api_key', (config as any).api_key || '');
      params.append('auth_type', config.auth_type || 'api_key');
      params.append('data_format', config.data_format || 'xml');
      params.append('sync_enabled', String(config.sync_enabled ?? true));
      params.append('sync_interval_minutes', String(config.sync_interval_minutes || 15));
      params.append('endpoint_attendance', config.endpoint_attendance || '');
      params.append('endpoint_employees', config.endpoint_employees || '');
      params.append('webhook_url', (config as any).webhook_url || '');
      params.append('webhook_secret', (config as any).webhook_secret || '');
      params.append('webhook_enabled', String(config.webhook_enabled ?? false));

      await api.post('/erp/config', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      setMessage({ type: 'success', text: 'ERP configuration saved successfully' });
      loadConfig();
    } catch (e: any) {
      setMessage({ type: 'error', text: e.response?.data?.detail || 'Failed to save config' });
    } finally {
      setSaving(false);
    }
  };

  const pushAttendance = async () => {
    setPushing(true);
    setMessage(null);
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const res = await api.post('/erp/push/attendance?' + params.toString());
      if (res.data.success) {
        setMessage({ type: 'success', text: `Pushed ${res.data.records_pushed} records to ERP` });
      } else {
        setMessage({ type: 'error', text: `Push failed: ${res.data.response}` });
      }
      loadSyncLogs();
    } catch (e: any) {
      setMessage({ type: 'error', text: e.response?.data?.detail || 'Push failed' });
    } finally {
      setPushing(false);
    }
  };

  const downloadExport = (type: 'attendance' | 'employees', format: 'xml' | 'json') => {
    const token = localStorage.getItem('access_token');
    const params = new URLSearchParams({ format });
    if (startDate && type === 'attendance') params.append('start_date', startDate);
    if (endDate && type === 'attendance') params.append('end_date', endDate);

    window.open(
      `${api.defaults.baseURL}/erp/export/${type}?${params.toString()}`,
      '_blank'
    );
  };

  const testWebhook = async () => {
    setMessage(null);
    try {
      const res = await api.post('/erp/webhook/test');
      if (res.data.success) {
        setMessage({ type: 'success', text: 'Webhook test successful' });
      } else {
        setMessage({ type: 'error', text: 'Webhook test failed' });
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e.response?.data?.detail || 'Webhook test failed' });
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        ERP Integration
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab icon={<SettingsIcon />} label="Configuration" />
        <Tab icon={<SyncIcon />} label="Export & Push" />
        <Tab icon={<WebhookIcon />} label="Webhooks" />
        <Tab icon={<DownloadIcon />} label="Sync Logs" />
      </Tabs>

      {tab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              ERP Connection Settings
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="ERP Name"
                  value={config.erp_name || ''}
                  onChange={(e) => setConfig({ ...config, erp_name: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="ERP URL"
                  value={config.erp_url || ''}
                  onChange={(e) => setConfig({ ...config, erp_url: e.target.value })}
                  placeholder="https://your-erp.com/api"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="API Key"
                  value={(config as any).api_key || ''}
                  onChange={(e) => setConfig({ ...config, api_key: e.target.value } as any)}
                  type="password"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Data Format"
                  select
                  value={config.data_format || 'xml'}
                  onChange={(e) => setConfig({ ...config, data_format: e.target.value })}
                >
                  <option value="xml">XML</option>
                  <option value="json">JSON</option>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Attendance Endpoint"
                  value={config.endpoint_attendance || ''}
                  onChange={(e) => setConfig({ ...config, endpoint_attendance: e.target.value })}
                  placeholder="https://your-erp.com/api/attendance"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Employees Endpoint"
                  value={config.endpoint_employees || ''}
                  onChange={(e) => setConfig({ ...config, endpoint_employees: e.target.value })}
                  placeholder="https://your-erp.com/api/employees"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={config.sync_enabled ?? true}
                      onChange={(e) => setConfig({ ...config, sync_enabled: e.target.checked })}
                    />
                  }
                  label="Enable Auto Sync"
                />
              </Grid>
              <Grid item xs={12}>
                <Button variant="contained" onClick={saveConfig} disabled={saving}>
                  {saving ? <CircularProgress size={20} /> : 'Save Configuration'}
                </Button>
              </Grid>
            </Grid>

            {config.last_sync_at && (
              <Alert severity={config.last_sync_status === 'success' ? 'success' : 'info'} sx={{ mt: 2 }}>
                Last sync: {new Date(config.last_sync_at).toLocaleString()} — {config.last_sync_status}
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {tab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Export & Push Data
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Start Date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="End Date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2} flexWrap="wrap">
                  <Button
                    variant="contained"
                    startIcon={<SyncIcon />}
                    onClick={pushAttendance}
                    disabled={pushing || !config.endpoint_attendance}
                  >
                    {pushing ? <CircularProgress size={20} /> : 'Push to ERP'}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => downloadExport('attendance', 'xml')}
                  >
                    Download Attendance (XML)
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => downloadExport('attendance', 'json')}
                  >
                    Download Attendance (JSON)
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => downloadExport('employees', 'xml')}
                  >
                    Download Employees (XML)
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => downloadExport('employees', 'json')}
                  >
                    Download Employees (JSON)
                  </Button>
                </Box>
              </Grid>
            </Grid>

            <Box mt={3}>
              <Typography variant="h6" gutterBottom>
                Public API Endpoints
              </Typography>
              <Alert severity="info">
                Your ERP can pull data directly using these endpoints with your API key:
              </Alert>
              <Box mt={1}>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: '#f5f5f5', p: 1, borderRadius: 1 }}>
                  GET /api/v1/erp/public/attendance?api_key=YOUR_KEY&format=xml
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: '#f5f5f5', p: 1, borderRadius: 1, mt: 1 }}>
                  GET /api/v1/erp/public/employees?api_key=YOUR_KEY&format=xml
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {tab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Webhook Configuration
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Webhook URL"
                  value={(config as any).webhook_url || ''}
                  onChange={(e) => setConfig({ ...config, webhook_url: e.target.value } as any)}
                  placeholder="https://your-erp.com/webhook/attendance"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Webhook Secret"
                  value={(config as any).webhook_secret || ''}
                  onChange={(e) => setConfig({ ...config, webhook_secret: e.target.value } as any)}
                  type="password"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={config.webhook_enabled ?? false}
                      onChange={(e) => setConfig({ ...config, webhook_enabled: e.target.checked })}
                    />
                  }
                  label="Enable Webhooks"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button variant="outlined" onClick={testWebhook} disabled={!config.webhook_enabled}>
                    Test Webhook
                  </Button>
                  <Button variant="contained" onClick={saveConfig} disabled={saving}>
                    Save Webhook Settings
                  </Button>
                </Box>
              </Grid>
            </Grid>

            <Box mt={3}>
              <Typography variant="h6" gutterBottom>
                Webhook Events
              </Typography>
              <Alert severity="info">
                When enabled, your ERP will receive POST requests to the webhook URL with event data:
              </Alert>
              <Box mt={1}>
                <Chip label="check_in" color="primary" sx={{ mr: 1 }} />
                <Chip label="check_out" color="secondary" sx={{ mr: 1 }} />
                <Chip label="face_enrolled" color="success" sx={{ mr: 1 }} />
                <Chip label="test" color="default" />
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {tab === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Sync History
            </Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Direction</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Records</TableCell>
                    <TableCell>Started</TableCell>
                    <TableCell>Error</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {syncLogs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        No sync logs found
                      </TableCell>
                    </TableRow>
                  ) : (
                    syncLogs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell>{log.sync_type}</TableCell>
                        <TableCell>{log.direction}</TableCell>
                        <TableCell>
                          <Chip
                            label={log.status}
                            color={log.status === 'success' ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{log.records_count}</TableCell>
                        <TableCell>
                          {log.started_at ? new Date(log.started_at).toLocaleString() : '-'}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {log.error_message || '-'}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
