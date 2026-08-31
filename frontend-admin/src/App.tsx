import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Departments from './pages/Departments';
import Employees from './pages/Employees';
import Attendance from './pages/Attendance';
import Reports from './pages/Reports';
import FaceEnrollment from './pages/FaceEnrollment';
import FaceRecognition from './pages/FaceRecognition';
import ERPIntegration from './pages/ERPIntegration';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';

const queryClient = new QueryClient();

const theme = createTheme({
  palette: {
    primary: {
      main: '#1a365d',
      light: '#2c5282',
      dark: '#0f2440',
    },
    secondary: {
      main: '#2b6cb0',
      light: '#3182ce',
      dark: '#1e4e8c',
    },
    background: {
      default: '#f0f2f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a202c',
      secondary: '#4a5568',
    },
    success: { main: '#2f855a' },
    warning: { main: '#c05621' },
    error: { main: '#c53030' },
    info: { main: '#2b6cb0' },
    divider: '#e2e8f0',
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    h4: { fontWeight: 700, fontSize: '1.5rem', color: '#1a202c' },
    h5: { fontWeight: 600, fontSize: '1.15rem' },
    h6: { fontWeight: 600, fontSize: '1rem' },
    subtitle1: { fontWeight: 500 },
    body2: { color: '#4a5568' },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
          border: '1px solid #e2e8f0',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none' as const,
          fontWeight: 600,
          borderRadius: 6,
          padding: '8px 16px',
        },
        contained: {
          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          borderRadius: 6,
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            backgroundColor: '#f7fafc',
            fontWeight: 700,
            fontSize: '0.75rem',
            textTransform: 'uppercase' as const,
            letterSpacing: '0.05em',
            color: '#4a5568',
            borderBottom: '2px solid #e2e8f0',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #edf2f7',
          padding: '12px 16px',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
        },
      },
    },
  },
});

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <ErrorBoundary>
            <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="departments" element={<Departments />} />
              <Route path="employees" element={<Employees />} />
              <Route path="attendance" element={<Attendance />} />
              <Route path="face-enrollment" element={<FaceEnrollment />} />
              <Route path="face-recognition" element={<FaceRecognition />} />
              <Route path="reports" element={<Reports />} />
              <Route path="erp-integration" element={<ERPIntegration />} />
            </Route>
            </Routes>
          </ErrorBoundary>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
