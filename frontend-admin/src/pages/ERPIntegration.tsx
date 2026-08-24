import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Sync as SyncIcon,
  Webhook as WebhookIcon,
  History as HistoryIcon,
  CloudUpload as CloudUploadIcon,
} from '@mui/icons-material';
import { erpAPI } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return value === index ? <Box sx={{ py: 3 }}>{children}</Box> : null;
}

export default function ERPIntegration() {
  const [tab, setTab] = useState(0);
  const [configForm, setConfigForm] = useState({
    erp_base_url: '',
    erp_api_key: '',
    export_format: 'xml',
    push_enabled: false,
    push_endpoint: '',
    push_auth_header: '',
    webhook_enabled: false,
    webhook_url: '',
    webhook_secret: '',
  });
  const [exportResult, setExportResult] = useState<any>(null);
  const [pushResult, setPushResult] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: config, isLoading: loadingConfig } = useQuery({
    queryKey: ['erpConfig'],
    queryFn: () => erpAPI.getConfig().then((res) => res.data),
  });

  const { data: logsData, isLoading: loadingLogs } = useQuery({
    queryKey: ['erpSyncLogs'],
    queryFn: () => erpAPI.getSyncLogs().then((res) => res.data),
  });

  const configMutation = useMutation({
    mutationFn: (data: any) => erpAPI.updateConfig(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['erpConfig'] }),
  });

  const exportMutation = useMutation({
    mutationFn: (params: any) => erpAPI.exportAttendance(params).then((res) => res.data),
    onSuccess: (data) => setExportResult(data),
  });

  const pushMutation = useMutation({
    mutationFn: () => erpAPI.pushAttendance().then((res) => res.data),
    onSuccess: (data) => setPushResult(data),
  });

  const webhookTestMutation = useMutation({
    mutationFn: () => erpAPI.testWebhook().then((res) => res.data),
  });

  React.useEffect(() => {
    if (config) {
      setConfigForm({
        erp_base_url: config.erp_base_url || '',
        erp_api_key: config.erp_api_key || '',
        export_format: config.export_format || 'xml',
        push_enabled: config.push_enabled || false,
        push_endpoint: config.push_endpoint || '',
        push_auth_header: config.push_auth_header || '',
        webhook_enabled: config.webhook_enabled || false,
        webhook_url: config.webhook_url || '',
        webhook_secret: config.webhook_secret || '',
      });
    }
  }, [config]);

  const handleSaveConfig = () => {
    configMutation.mutate(configForm);
  };

  const handleExport = (type: string) => {
    exportMutation.mutate({
      export_type: type,
      start_date: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0],
      format: configForm.export_format,
    });
  };

  const getLogStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS': return { bg: '#f0fff4', color: '#2f855a' };
      case 'FAILED': return { bg: '#fff5f5', color: '#c53030' };
      case 'PARTIAL': return { bg: '#fffaf0', color: '#c05621' };
      default: return { bg: '#f7fafc', color: '#4a5568' };
    }
  };

  const logs = logsData?.logs || [];

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>ERP Integration</Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Configure and manage your ERP system integration
        </Typography>
      </Box>

      <Card>
        <CardContent sx={{ p: 0 }}>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v)}
            sx={{ borderBottom: 1, borderColor: '#e2e8f0', px: 2 }}
          >
            <Tab icon={<SettingsIcon />} iconPosition="start" label="Configuration" />
            <Tab icon={<SyncIcon />} iconPosition="start" label="Export & Push" />
            <Tab icon={<WebhookIcon />} iconPosition="start" label="Webhooks" />
            <Tab icon={<HistoryIcon />} iconPosition="start" label="Sync Logs" />
          </Tabs>

          {/* Configuration Tab */}
          <TabPanel value={tab} index={0}>
            <Box sx={{ px: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>ERP Server Configuration</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" label="ERP Base URL" placeholder="https://your-erp.com/api" value={configForm.erp_base_url} onChange={(e) => setConfigForm({ ...configForm, erp_base_url: e.target.value })} />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" label="API Key" value={configForm.erp_api_key} onChange={(e) => setConfigForm({ ...configForm, erp_api_key: e.target.value })} />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" select label="Export Format" value={configForm.export_format} onChange={(e) => setConfigForm({ ...configForm, export_format: e.target.value })}>
                    <MenuItem value="xml">XML</MenuItem>
                    <MenuItem value="json">JSON</MenuItem>
                  </TextField>
                </Grid>
              </Grid>

              <Divider sx={{ my: 3 }} />

              <Typography variant="h6" sx={{ mb: 2 }}>Push Configuration</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel control={<Switch checked={configForm.push_enabled} onChange={(e) => setConfigForm({ ...configForm, push_enabled: e.target.checked })} />} label="Enable auto-push to ERP" />
                </Grid>
                {configForm.push_enabled && (
                  <>
                    <Grid item xs={12} md={8}>
                      <TextField fullWidth size="small" label="Push Endpoint" placeholder="https://your-erp.com/api/attendance/import" value={configForm.push_endpoint} onChange={(e) => setConfigForm({ ...configForm, push_endpoint: e.target.value })} />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField fullWidth size="small" label="Auth Header" placeholder="Bearer token..." value={configForm.push_auth_header} onChange={(e) => setConfigForm({ ...configForm, push_auth_header: e.target.value })} />
                    </Grid>
                  </>
                )}
              </Grid>

              <Box sx={{ mt: 3 }}>
                <Button variant="contained" onClick={handleSaveConfig} disabled={configMutation.isPending}>
                  {configMutation.isPending ? 'Saving...' : 'Save Configuration'}
                </Button>
                {configMutation.isSuccess && <Alert severity="success" sx={{ mt: 1 }}>Configuration saved</Alert>}
              </Box>
            </Box>
          </TabPanel>

          {/* Export & Push Tab */}
          <TabPanel value={tab} index={1}>
            <Box sx={{ px: 3 }}>
              <Grid container spacing={2.5}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ mb: 1 }}>Export Attendance Data</Typography>
                      <Typography variant="body2" sx={{ color: '#718096', mb: 2 }}>
                        Generate XML or JSON export for the last 30 days
                      </Typography>
                      <Button variant="contained" startIcon={<CloudUploadIcon />} onClick={() => handleExport('attendance')} disabled={exportMutation.isPending} fullWidth>
                        {exportMutation.isPending ? 'Exporting...' : 'Export Attendance'}
                      </Button>
                      {exportResult && (
                        <Alert severity="success" sx={{ mt: 2 }}>
                          Export generated: {exportResult.filename || 'Success'}
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ mb: 1 }}>Push to ERP</Typography>
                      <Typography variant="body2" sx={{ color: '#718096', mb: 2 }}>
                        Send attendance data to the configured ERP endpoint
                      </Typography>
                      <Button variant="contained" color="secondary" startIcon={<SyncIcon />} onClick={() => pushMutation.mutate()} disabled={pushMutation.isPending || !configForm.push_enabled} fullWidth>
                        {pushMutation.isPending ? 'Pushing...' : 'Push Attendance Data'}
                      </Button>
                      {!configForm.push_enabled && (
                        <Alert severity="info" sx={{ mt: 2 }}>Enable push in Configuration tab first</Alert>
                      )}
                      {pushResult && (
                        <Alert severity={pushResult.success ? 'success' : 'error'} sx={{ mt: 2 }}>
                          {pushResult.message || (pushResult.success ? 'Push completed' : 'Push failed')}
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          </TabPanel>

          {/* Webhooks Tab */}
          <TabPanel value={tab} index={2}>
            <Box sx={{ px: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Webhook Configuration</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel control={<Switch checked={configForm.webhook_enabled} onChange={(e) => setConfigForm({ ...configForm, webhook_enabled: e.target.checked })} />} label="Enable webhooks" />
                </Grid>
                <Grid item xs={12} md={8}>
                  <TextField fullWidth size="small" label="Webhook URL" placeholder="https://your-system.com/webhook/attendance" value={configForm.webhook_url} onChange={(e) => setConfigForm({ ...configForm, webhook_url: e.target.value })} disabled={!configForm.webhook_enabled} />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField fullWidth size="small" label="Webhook Secret" value={configForm.webhook_secret} onChange={(e) => setConfigForm({ ...configForm, webhook_secret: e.target.value })} disabled={!configForm.webhook_enabled} />
                </Grid>
              </Grid>
              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button variant="contained" onClick={handleSaveConfig} disabled={configMutation.isPending}>
                  Save
                </Button>
                <Button variant="outlined" onClick={() => webhookTestMutation.mutate()} disabled={!configForm.webhook_enabled || webhookTestMutation.isPending}>
                  {webhookTestMutation.isPending ? 'Testing...' : 'Test Webhook'}
                </Button>
              </Box>
              {webhookTestMutation.isSuccess && <Alert severity="success" sx={{ mt: 2 }}>Webhook test sent</Alert>}
            </Box>
          </TabPanel>

          {/* Sync Logs Tab */}
          <TabPanel value={tab} index={3}>
            <Box sx={{ px: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Sync History</Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Format</TableCell>
                      <TableCell>Records</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Typography variant="body2" sx={{ color: '#a0aec0', textAlign: 'center', py: 4 }}>
                            No sync logs yet
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      logs.map((log: any) => {
                        const st = getLogStatusColor(log.status);
                        return (
                          <TableRow key={log.id} hover>
                            <TableCell>
                              <Typography variant="body2" sx={{ color: '#718096' }}>
                                {log.created_at ? new Date(log.created_at).toLocaleString() : '-'}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip label={log.sync_type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                            </TableCell>
                            <TableCell>{log.export_format || '-'}</TableCell>
                            <TableCell>{log.records_count || 0}</TableCell>
                            <TableCell>
                              <Chip label={log.status} size="small" sx={{ backgroundColor: st.bg, color: st.color, fontWeight: 600, fontSize: '0.7rem' }} />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" sx={{ color: '#718096', fontSize: '0.8rem' }}>
                                {log.error_message || log.message || '-'}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </TabPanel>
        </CardContent>
      </Card>
    </Box>
  );
}
