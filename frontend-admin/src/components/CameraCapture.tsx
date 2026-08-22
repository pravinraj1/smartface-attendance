import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  IconButton,
  Paper,
  Stack,
  CircularProgress,
} from '@mui/material';
import {
  CameraAlt as CameraIcon,
  FlipCameraAndroid as FlipIcon,
  Stop as StopIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';

interface CameraCaptureProps {
  onCapture: (blob: Blob) => void;
  onClose?: () => void;
  disabled?: boolean;
  captureCount?: number;
}

export default function CameraCapture({
  onCapture,
  onClose,
  disabled = false,
  captureCount = 1,
}: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user');
  const [capturedImages, setCapturedImages] = useState<string[]>([]);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [cameraError, setCameraError] = useState<string>('');
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async () => {
    try {
      setCameraError('');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setStreaming(true);
    } catch (err: any) {
      console.error('Camera access error:', err);
      if (err.name === 'NotAllowedError') {
        setCameraError('Camera permission denied. Please allow camera access in your browser settings and reload, or use the Upload Image button.');
      } else if (err.name === 'NotFoundError') {
        setCameraError('No camera found. Please connect a webcam and reload, or use the Upload Image button.');
      } else {
        setCameraError('Camera error: ' + (err.message || 'Unknown error') + '. Try the Upload Image button.');
      }
    }
  }, [facingMode]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  }, []);

  const flipCamera = useCallback(() => {
    stopCamera();
    setFacingMode((prev) => (prev === 'user' ? 'environment' : 'user'));
  }, [stopCamera]);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return new Promise<Blob>((resolve) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
      }, 'image/jpeg', 0.9);
    });
  }, []);

  const handleCapture = useCallback(async () => {
    if (disabled || countdown !== null) return;
    setCountdown(3);
  }, [disabled, countdown]);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown === 0) {
      (async () => {
        const blob = await capturePhoto();
        if (blob) {
          const url = URL.createObjectURL(blob);
          setCapturedImages((prev) => [...prev, url]);
          onCapture(blob);
        }
        setCountdown(null);
      })();
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => (c !== null ? c - 1 : null)), 1000);
    return () => clearTimeout(timer);
  }, [countdown, capturePhoto, onCapture]);

  useEffect(() => {
    if (streaming) return;
    startCamera();
    return () => stopCamera();
  }, []);

  return (
    <Paper
      variant="outlined"
      sx={{
        position: 'relative',
        overflow: 'hidden',
        borderRadius: 2,
        bgcolor: '#000',
        aspectRatio: '4/3',
        maxHeight: 400,
      }}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: facingMode === 'user' ? 'scaleX(-1)' : 'none',
        }}
      />
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Face guide overlay */}
      {streaming && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 200,
            height: 250,
            border: '3px dashed rgba(255,255,255,0.7)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Countdown overlay */}
      {countdown !== null && countdown > 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(0,0,0,0.5)',
          }}
        >
          <Typography variant="h1" sx={{ color: '#fff', fontSize: 80 }}>
            {countdown}
          </Typography>
        </Box>
      )}

      {/* Captured check */}
      {!streaming && capturedImages.length > 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(0,0,0,0.4)',
          }}
        >
          <CheckIcon sx={{ fontSize: 80, color: 'success.main' }} />
        </Box>
      )}

      {/* Camera error */}
      {!streaming && cameraError && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(0,0,0,0.8)',
            p: 3,
          }}
        >
          <CameraIcon sx={{ fontSize: 48, color: 'warning.main', mb: 2 }} />
          <Typography variant="body1" sx={{ color: '#fff', textAlign: 'center', mb: 2 }}>
            {cameraError}
          </Typography>
          <Button
            variant="contained"
            onClick={() => { setCameraError(''); startCamera(); }}
            sx={{ color: '#fff' }}
          >
            Retry Camera
          </Button>
        </Box>
      )}

      {/* Controls */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 2,
        }}
      >
        <IconButton onClick={flipCamera} sx={{ bgcolor: 'rgba(0,0,0,0.5)', color: '#fff' }}>
          <FlipIcon />
        </IconButton>
        <IconButton
          onClick={handleCapture}
          disabled={disabled || !streaming || countdown !== null}
          sx={{
            bgcolor: 'rgba(0,0,0,0.5)',
            color: '#fff',
            width: 64,
            height: 64,
            border: '3px solid #fff',
            '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' },
          }}
        >
          <CameraIcon sx={{ fontSize: 32 }} />
        </IconButton>
        <IconButton onClick={stopCamera} sx={{ bgcolor: 'rgba(0,0,0,0.5)', color: '#fff' }}>
          <StopIcon />
        </IconButton>
      </Box>

      {/* Status bar */}
      <Box
        sx={{
          position: 'absolute',
          top: 12,
          left: 12,
          right: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: '#fff',
            bgcolor: streaming ? 'success.main' : 'error.main',
            px: 1,
            py: 0.5,
            borderRadius: 1,
          }}
        >
          {streaming ? 'LIVE' : 'OFFLINE'}
        </Typography>
        <Typography variant="caption" sx={{ color: '#fff', bgcolor: 'rgba(0,0,0,0.5)', px: 1, py: 0.5, borderRadius: 1 }}>
          {capturedImages.length} / {captureCount}
        </Typography>
      </Box>
    </Paper>
  );
}
