import React from 'react';
import { Box, Typography, Button } from '@mui/material';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error?.message || String(error) };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('SmartFace UI error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
            Something went wrong
          </Typography>
          <Typography variant="body2" sx={{ color: '#718096', mb: 2 }}>
            {this.state.message || 'An unexpected error occurred.'}
          </Typography>
          <Button
            variant="contained"
            onClick={() => { this.setState({ hasError: false, message: '' }); window.location.reload(); }}
          >
            Reload
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
