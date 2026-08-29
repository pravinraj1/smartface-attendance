import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data),
  refreshToken: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
  getMe: () => api.get('/auth/me'),
};

export const departmentAPI = {
  getAll: (params?: { is_active?: boolean }) =>
    api.get('/departments', { params }),
  getById: (id: string) => api.get(`/departments/${id}`),
  create: (data: { name: string; description?: string }) =>
    api.post('/departments', data),
  update: (id: string, data: { name?: string; description?: string; is_active?: boolean }) =>
    api.put(`/departments/${id}`, data),
  delete: (id: string) => api.delete(`/departments/${id}`),
};

export const employeeAPI = {
  getAll: (params?: { skip?: number; limit?: number; search?: string; department_id?: string }) =>
    api.get('/employees', { params }),
  getById: (id: string) => api.get(`/employees/${id}`),
  create: (data: any) => api.post('/employees', data),
  update: (id: string, data: any) => api.put(`/employees/${id}`, data),
  delete: (id: string) => api.delete(`/employees/${id}`),
};

export const attendanceAPI = {
  getAll: (params?: { skip?: number; limit?: number; employee_id?: string; start_date?: string; end_date?: string }) =>
    api.get('/attendance', { params }),
  getToday: () => api.get('/attendance/today'),
  getStats: () => api.get('/attendance/stats'),
  getEmployeeAttendance: (employeeId: string, params?: { start_date?: string; end_date?: string }) =>
    api.get(`/attendance/employee/${employeeId}`, { params }),
  checkIn: (data: { employee_id: string; confidence_score: number; snapshot_url?: string }) =>
    api.post('/attendance/checkin', data),
  checkOut: (data: { employee_id: string; confidence_score: number; snapshot_url?: string }) =>
    api.post('/attendance/checkout', data),
  getLogs: (params?: { skip?: number; limit?: number; employee_id?: string; event_type?: string }) =>
    api.get('/attendance/logs', { params }),
  getLiveFeed: (limit: number = 20) =>
    api.get('/attendance/logs/live', { params: { limit } }),
};

export const faceAPI = {
  enroll: (employeeId: string, image: string) =>
    api.post(`/faces/enroll`, { employee_id: employeeId, image_data: image }),
  getEmployeeFaces: (employeeId: string) =>
    api.get(`/faces/employee/${employeeId}`),
  delete: (faceId: string) => api.delete(`/faces/${faceId}`),
  recognize: (image: string) =>
    api.post('/faces/recognize', { image_data: image }),
  getRecognitionLogs: (limit: number = 50) =>
    api.get('/faces/recognize/logs', { params: { limit } }),
  checkDuplicate: (image: string, excludeEmployeeId?: string) =>
    api.post('/faces/check-duplicate', { image, exclude_employee_id: excludeEmployeeId }),
};

export const reportsAPI = {
  getSummary: (params?: { start_date?: string; end_date?: string; department_id?: string }) =>
    api.get('/reports/summary', { params }),
  getEmployeeReport: (employeeId: string, params?: { start_date?: string; end_date?: string }) =>
    api.get(`/reports/employee/${employeeId}`, { params }),
  getDepartmentReport: (departmentId: string, params?: { start_date?: string; end_date?: string }) =>
    api.get(`/reports/department/${departmentId}`, { params }),
  exportSummary: (params?: { start_date?: string; end_date?: string; department_id?: string }) =>
    api.get('/reports/summary', { params: { ...params, format: 'csv' }, responseType: 'blob' }),
};

export const erpAPI = {
  getConfig: () => api.get('/erp/config'),
  updateConfig: (data: any) => api.post('/erp/config', data),
  exportAttendance: (params: any) => api.get('/erp/export/attendance', { params }),
  exportEmployees: (params: any) => api.get('/erp/export/employees', { params }),
  pushAttendance: () => api.post('/erp/push/attendance'),
  testWebhook: () => api.post('/erp/webhook/test'),
  getSyncLogs: (params?: { skip?: number; limit?: number }) =>
    api.get('/erp/sync-logs', { params }),
};

export default api;
