import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Business as BusinessIcon,
  People as PeopleIcon,
  AccessTime as AccessTimeIcon,
  Assessment as AssessmentIcon,
  Face as FaceIcon,
  Visibility as VisibilityIcon,
  ExitToApp as ExitToAppIcon,
  Sync as SyncIcon,
  Person as PersonIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material';

const drawerWidth = 260;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { text: 'Departments', icon: <BusinessIcon />, path: '/departments' },
  { text: 'Employees', icon: <PeopleIcon />, path: '/employees' },
  { text: 'Attendance', icon: <AccessTimeIcon />, path: '/attendance' },
  { text: 'Face Enrollment', icon: <FaceIcon />, path: '/face-enrollment' },
  { text: 'Face Recognition', icon: <VisibilityIcon />, path: '/face-recognition' },
  { text: 'Reports', icon: <AssessmentIcon />, path: '/reports' },
  { divider: true },
  { text: 'ERP Integration', icon: <SyncIcon />, path: '/erp-integration' },
];

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Logo */}
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <FaceIcon sx={{ color: 'white', fontSize: 20 }} />
        </Box>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#1a202c', lineHeight: 1.2 }}>
            SmartFace
          </Typography>
          <Typography variant="caption" sx={{ color: '#718096', fontSize: '0.65rem' }}>
            Attendance System
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ mx: 2 }} />

      {/* Navigation */}
      <List sx={{ flex: 1, px: 1.5, py: 1 }}>
        {menuItems.map((item, index) => {
          if ('divider' in item && item.divider) {
            return <Divider key={`div-${index}`} sx={{ my: 1 }} />;
          }
          const isActive = location.pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected={isActive}
                onClick={() => {
                  if ('path' in item) navigate((item as { path: string }).path);
                  setMobileOpen(false);
                }}
                sx={{
                  borderRadius: '8px',
                  minHeight: 42,
                  px: 1.5,
                  backgroundColor: isActive ? '#ebf4ff' : 'transparent',
                  '&:hover': { backgroundColor: '#edf2f7' },
                  '&.Mui-selected': { backgroundColor: '#ebf4ff' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: isActive ? '#2b6cb0' : '#718096' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  slotProps={{
                    primary: {
                      sx: {
                        fontSize: '0.875rem',
                        fontWeight: isActive ? 600 : 500,
                        color: isActive ? '#2b6cb0' : '#4a5568',
                      },
                    },
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: '1px solid #e2e8f0' }}>
        <Chip
          label="v1.0.0"
          size="small"
          variant="outlined"
          sx={{ fontSize: '0.65rem', height: 20 }}
        />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          backgroundColor: 'white',
          borderBottom: '1px solid #e2e8f0',
          color: '#1a202c',
        }}
      >
        <Toolbar sx={{ minHeight: '56px !important' }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Box sx={{ flexGrow: 1 }} />

          <IconButton onClick={handleMenuOpen} sx={{ p: 0.5 }}>
            <Avatar
              sx={{
                width: 34,
                height: 34,
                bgcolor: '#1a365d',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              <PersonIcon fontSize="small" />
            </Avatar>
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            slotProps={{ paper: { sx: { mt: 1, minWidth: 160, borderRadius: 2 } } }}
          >
            <MenuItem onClick={handleLogout} sx={{ py: 1 }}>
              <ListItemIcon><ExitToAppIcon fontSize="small" /></ListItemIcon>
              Sign Out
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              borderRight: '1px solid #e2e8f0',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: '#f0f2f5',
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
