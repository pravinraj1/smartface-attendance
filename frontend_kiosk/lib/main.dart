import 'dart:async';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:math';

const String kApiPrefix = '/api/v1';
const String kDefaultUrl = 'https://smartface-attendance-7ygu.onrender.com';
const Duration kHttpTimeout = Duration(seconds: 15);
const Duration kFaceRecognitionTimeout = Duration(seconds: 30);
const Duration kServerCheckInterval = Duration(seconds: 30);

typedef TokenResolver = Future<String?> Function({bool force});

Future<http.Response> _sendAuthed(
  TokenResolver resolve,
  Future<http.Response> Function(String? token) request,
) async {
  var token = await resolve();
  var response = await request(token);
  if (response.statusCode == 401) {
    final fresh = await resolve(force: true);
    if (fresh != null) {
      response = await request(fresh);
    }
  }
  return response;
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final cameras = await availableCameras();
  final frontCam = cameras.firstWhere(
    (c) => c.lensDirection == CameraLensDirection.front,
    orElse: () => cameras.first,
  );
  final prefs = await SharedPreferences.getInstance();
  final savedIp = kIsWeb ? '' : (prefs.getString('server_ip') ?? kDefaultUrl);
  runApp(MyApp(cameras: [frontCam], serverIp: savedIp));
}

class MyApp extends StatelessWidget {
  final List<CameraDescription> cameras;
  final String serverIp;
  const MyApp({super.key, required this.cameras, required this.serverIp});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartFace Kiosk',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: KioskHome(cameras: cameras, serverIp: serverIp),
      debugShowCheckedModeBanner: false,
    );
  }
}

class KioskHome extends StatefulWidget {
  final List<CameraDescription> cameras;
  final String serverIp;
  const KioskHome({super.key, required this.cameras, required this.serverIp});

  @override
  State<KioskHome> createState() => _KioskHomeState();
}

class _KioskHomeState extends State<KioskHome> {
  int _currentMode = 0;
  late String _serverIp;
  String? _authToken;
  bool _serverOnline = false;
  String _serverError = '';
  Timer? _serverHealthTimer;

  String get kApiBaseUrl {
    if (kIsWeb) return Uri.base.origin;
    if (_serverIp.startsWith('http')) return _serverIp;
    return 'http://$_serverIp:8080';
  }

  @override
  void initState() {
    super.initState();
    _serverIp = widget.serverIp;
    _login();
    _startServerHealthCheck();
  }

  @override
  void dispose() {
    _serverHealthTimer?.cancel();
    super.dispose();
  }

  void _startServerHealthCheck() {
    _checkServerHealth();
    _serverHealthTimer = Timer.periodic(kServerCheckInterval, (_) {
      _checkServerHealth();
    });
  }

  Future<void> _checkServerHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$kApiBaseUrl/health'),
      ).timeout(kHttpTimeout);
      final wasOffline = !_serverOnline;
      setState(() {
        _serverOnline = response.statusCode == 200;
        _serverError = '';
      });
      if (wasOffline && _serverOnline) {
        _login();
      }
    } catch (e) {
      setState(() {
        _serverOnline = false;
        _serverError = 'Server unavailable';
      });
    }
  }

  Future<void> _login() async {
    try {
      final response = await http.post(
        Uri.parse('$kApiBaseUrl$kApiPrefix/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': 'admin@smartface.com', 'password': 'Admin123!'}),
      ).timeout(kHttpTimeout);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _authToken = data['access_token'];
          _serverOnline = true;
          _serverError = '';
        });
      } else {
        setState(() {
          _serverError = 'Login failed (${response.statusCode})';
        });
      }
    } catch (e) {
      setState(() {
        _serverError = 'Cannot connect to server';
      });
      debugPrint('Login failed: $e');
    }
  }

  Future<String?> _ensureToken({bool force = false}) async {
    if (_authToken == null || force) {
      await _login();
    }
    return _authToken;
  }

  void _showSettings() {
    final controller = TextEditingController(text: _serverIp);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server Settings'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Server URL',
            hintText: 'e.g. https://smartface-attendance-7ygu.onrender.com',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final newIp = controller.text.trim();
              if (newIp.isNotEmpty) {
                final prefs = await SharedPreferences.getInstance();
                await prefs.setString('server_ip', newIp);
                setState(() {
                  _serverIp = newIp;
                  _authToken = null;
                  _serverOnline = false;
                  _serverError = 'Connecting...';
                });
                Navigator.pop(context);
                await _checkServerHealth();
                _login();
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          _currentMode == 0
              ? AttendanceMode(
                  key: ValueKey('att_$_serverIp'),
                  cameras: widget.cameras,
                  apiBaseUrl: kApiBaseUrl,
                  tokenResolver: _ensureToken,
                  onSettings: _showSettings,
                )
              : EnrollmentMode(
                  key: ValueKey('enr_$_serverIp'),
                  cameras: widget.cameras,
                  apiBaseUrl: kApiBaseUrl,
                  tokenResolver: _ensureToken,
                  onSettings: _showSettings,
                ),
          // Server offline banner
          if (!_serverOnline && _serverError.isNotEmpty)
            Positioned(
              top: 0, left: 0, right: 0,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                color: Colors.red.shade800,
                child: Row(
                  children: [
                    const Icon(Icons.cloud_off, color: Colors.white, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _serverError,
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                    ),
                    GestureDetector(
                      onTap: () async {
                        setState(() => _serverError = 'Reconnecting...');
                        await _checkServerHealth();
                        if (_serverOnline) _login();
                      },
                      child: const Text('RETRY', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentMode,
        onDestinationSelected: (i) => setState(() => _currentMode = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.face), label: 'Attendance'),
          NavigationDestination(icon: Icon(Icons.person_add), label: 'Enrollment'),
        ],
      ),
    );
  }
}

class AttendanceMode extends StatefulWidget {
  final List<CameraDescription> cameras;
  final String apiBaseUrl;
  final TokenResolver tokenResolver;
  final VoidCallback onSettings;
  const AttendanceMode({
    super.key,
    required this.cameras,
    required this.apiBaseUrl,
    required this.tokenResolver,
    required this.onSettings,
  });

  @override
  State<AttendanceMode> createState() => _AttendanceModeState();
}

class _AttendanceModeState extends State<AttendanceMode> with SingleTickerProviderStateMixin {
  late CameraController _controller;
  late Future<void> _initFuture;
  String _status = 'Initializing...';
  String _employeeName = '';
  String _employeeCode = '';
  bool _isProcessing = false;
  int _recognitionCount = 0;
  Timer? _autoScanTimer;
  bool _scanning = false;
  String _lastAction = '';
  DateTime? _lastScanTime;
  DateTime? _lastSuccessTime;
  int _cooldownSeconds = 5;

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _initCamera(widget.cameras[0]);
    _startAutoScan();
  }

  void _initCamera(CameraDescription cam) {
    _controller = CameraController(cam, ResolutionPreset.medium, enableAudio: false);
    _initFuture = _controller.initialize();
  }

  @override
  void dispose() {
    _autoScanTimer?.cancel();
    _pulseController.dispose();
    _controller.dispose();
    super.dispose();
  }

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  void _startAutoScan() {
    _autoScanTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      _autoScan();
    });
  }

  Future<void> _autoScan() async {
    if (!_controller.value.isInitialized || _isProcessing) return;

    final token = await widget.tokenResolver();
    if (token == null) {
      setState(() => _status = 'Waiting for server...');
      return;
    }

    if (_lastSuccessTime != null) {
      final elapsed = DateTime.now().difference(_lastSuccessTime!).inSeconds;
      if (elapsed < _cooldownSeconds) return;
    }

    setState(() {
      _isProcessing = true;
      _scanning = true;
      _status = 'Scanning...';
    });

    try {
      final XFile image = await _controller.takePicture();
      final bytes = await image.readAsBytes();
      final b64 = base64Encode(bytes);

      final response = await _sendAuthed(widget.tokenResolver, (token) => http.post(
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/faces/recognize'),
        headers: _headers(token),
        body: json.encode({'image_data': b64}),
      ).timeout(kFaceRecognitionTimeout));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['recognized'] == true) {
          final employeeId = data['employee_id'] ?? '';
          final name = data['employee_name'] ?? 'Unknown';
          final code = data['employee_code'] ?? '';
          final confidence = data['confidence'] ?? 0.0;

          setState(() {
            _employeeName = name;
            _employeeCode = code;
            _status = 'CHECK-IN SUCCESS';
            _lastAction = 'CHECK-IN';
            _recognitionCount++;
            _lastSuccessTime = DateTime.now();
          });

          final checkinResponse = await _sendAuthed(widget.tokenResolver, (token) => http.post(
            Uri.parse('${widget.apiBaseUrl}$kApiPrefix/attendance/checkin'),
            headers: _headers(token),
            body: json.encode({'employee_id': employeeId, 'confidence_score': confidence}),
          ).timeout(kHttpTimeout));

          if (checkinResponse.statusCode == 200) {
            final checkinData = json.decode(checkinResponse.body);
            setState(() => _status = 'CHECK-IN SUCCESS');
          } else {
            final errBody = json.decode(checkinResponse.body);
            final msg = errBody['detail'] ?? '';
            if (msg.toString().toLowerCase().contains('already checked in')) {
              setState(() => _status = 'Checking out...');
              final checkoutResponse = await _sendAuthed(widget.tokenResolver, (token) => http.post(
                Uri.parse('${widget.apiBaseUrl}$kApiPrefix/attendance/checkout'),
                headers: _headers(token),
                body: json.encode({'employee_id': employeeId, 'confidence_score': confidence}),
              ).timeout(kHttpTimeout));
              if (checkoutResponse.statusCode == 200) {
                setState(() {
                  _status = 'CHECK-OUT SUCCESS';
                  _lastAction = 'CHECK-OUT';
                });
              } else {
                final checkoutErr = json.decode(checkoutResponse.body);
                setState(() => _status = checkoutErr['detail'] ?? 'Checkout failed');
              }
            } else {
              setState(() => _status = msg.toString());
            }
          }

          await Future.delayed(const Duration(seconds: 3));
          setState(() {
            _status = 'Ready for attendance';
            _employeeName = '';
            _employeeCode = '';
          });
        } else {
          setState(() {
            _status = 'Face not recognized - Tap to select name';
          });
        }
      } else if (response.statusCode == 401) {
        setState(() => _status = 'Auth expired - check server');
      } else {
        setState(() => _status = 'Server error (${response.statusCode})');
      }
    } on TimeoutException {
      setState(() => _status = 'Server timeout - try again');
    } catch (e) {
      setState(() => _status = 'Connection error - retrying...');
    } finally {
      setState(() {
        _isProcessing = false;
        _scanning = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        FutureBuilder<void>(
          future: _initFuture,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.done) return CameraPreview(_controller);
            return const Center(child: CircularProgressIndicator(color: Colors.white));
          },
        ),
        Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: _status.contains('SUCCESS')
                  ? Colors.green
                  : _status.contains('Scanning')
                      ? Colors.blue
                      : Colors.white54,
              width: 4,
            ),
          ),
        ),
        if (_scanning)
          CustomPaint(
            painter: ScannerCornerPainter(color: Colors.blue),
          ),
        Positioned(
          top: 50, left: 0, right: 0,
          child: Column(children: [
            const Text('SMARTFACE', style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text(_status, style: TextStyle(
              color: _status.contains('SUCCESS') ? Colors.green : Colors.white,
              fontSize: 24, fontWeight: FontWeight.bold,
            )),
            const SizedBox(height: 5),
            Text(DateTime.now().toString().substring(0, 16), style: const TextStyle(color: Colors.white70, fontSize: 16)),
          ]),
        ),
        if (_scanning)
          Positioned(
            top: 150, left: 0, right: 0,
            child: Center(
              child: AnimatedBuilder(
                animation: _pulseAnimation,
                builder: (context, child) {
                  return Opacity(
                    opacity: _pulseAnimation.value,
                    child: Container(
                      width: 20, height: 20,
                      decoration: BoxDecoration(
                        color: Colors.blue,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.blue.withAlpha(100),
                            blurRadius: 10 * _pulseAnimation.value,
                            spreadRadius: 5 * _pulseAnimation.value,
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        if (_employeeName.isNotEmpty)
          Positioned(
            bottom: 100, left: 40, right: 40,
            child: Container(
              padding: const EdgeInsets.all(30),
              decoration: BoxDecoration(color: Colors.black.withAlpha(204), borderRadius: BorderRadius.circular(20)),
              child: Column(children: [
                Icon(
                  _lastAction == 'CHECK-OUT' ? Icons.logout : Icons.check_circle,
                  color: Colors.green,
                  size: 80,
                ),
                const SizedBox(height: 20),
                Text(
                  _lastAction == 'CHECK-OUT' ? 'GOODBYE' : 'WELCOME',
                  style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 10),
                Text(_employeeName, style: const TextStyle(color: Colors.white, fontSize: 24)),
                if (_employeeCode.isNotEmpty)
                  Text(_employeeCode, style: const TextStyle(color: Colors.grey, fontSize: 16)),
                const SizedBox(height: 10),
                Text(DateTime.now().toString().substring(11, 16), style: const TextStyle(color: Colors.white, fontSize: 20)),
              ]),
            ),
          ),
        Positioned(
          bottom: 30, right: 30,
          child: Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(color: Colors.black.withAlpha(153), borderRadius: BorderRadius.circular(8)),
              child: Text('Scans: $_recognitionCount', style: const TextStyle(color: Colors.white70, fontSize: 14)),
            ),
            const SizedBox(width: 10),
            GestureDetector(
              onTap: widget.onSettings,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: Colors.black.withAlpha(153), borderRadius: BorderRadius.circular(8)),
                child: const Icon(Icons.settings, color: Colors.white70, size: 28),
              ),
            ),
          ]),
        ),
      ],
    );
  }
}

class ScannerCornerPainter extends CustomPainter {
  final Color color;
  ScannerCornerPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 4
      ..style = PaintingStyle.stroke;

    const len = 40.0;
    const inset = 20.0;

    canvas.drawLine(const Offset(inset, inset), const Offset(inset + len, inset), paint);
    canvas.drawLine(const Offset(inset, inset), const Offset(inset, inset + len), paint);
    canvas.drawLine(Offset(size.width - inset, inset), Offset(size.width - inset - len, inset), paint);
    canvas.drawLine(Offset(size.width - inset, inset), Offset(size.width - inset, inset + len), paint);
    canvas.drawLine(Offset(inset, size.height - inset), Offset(inset + len, size.height - inset), paint);
    canvas.drawLine(Offset(inset, size.height - inset), Offset(inset, size.height - inset - len), paint);
    canvas.drawLine(Offset(size.width - inset, size.height - inset), Offset(size.width - inset - len, size.height - inset), paint);
    canvas.drawLine(Offset(size.width - inset, size.height - inset), Offset(size.width - inset, size.height - inset - len), paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class EnrollmentMode extends StatefulWidget {
  final List<CameraDescription> cameras;
  final String apiBaseUrl;
  final TokenResolver tokenResolver;
  final VoidCallback onSettings;
  const EnrollmentMode({
    super.key,
    required this.cameras,
    required this.apiBaseUrl,
    required this.tokenResolver,
    required this.onSettings,
  });

  @override
  State<EnrollmentMode> createState() => _EnrollmentModeState();
}

class _EnrollmentModeState extends State<EnrollmentMode> {
  late CameraController _controller;
  late Future<void> _initFuture;
  List<dynamic> _employees = [];
  String? _selectedEmployeeId;
  String _selectedEmployeeName = '';
  bool _loadingEmployees = true;
  bool _loadFailed = false;
  bool _isCapturing = false;
  bool _isUploading = false;
  String _resultMessage = '';
  bool _resultSuccess = false;
  XFile? _lastCapture;
  bool _isDuplicateCheckRunning = false;
  String _duplicateWarning = '';
  bool _isDuplicate = false;

  @override
  void initState() {
    super.initState();
    _initCamera(widget.cameras[0]);
    _fetchEmployees();
  }

  void _initCamera(CameraDescription cam) {
    _controller = CameraController(cam, ResolutionPreset.medium, enableAudio: false);
    _initFuture = _controller.initialize();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Future<void> _fetchEmployees() async {
    try {
      final response = await _sendAuthed(widget.tokenResolver, (token) => http.get(
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/employees?limit=500'),
        headers: _headers(token),
      ).timeout(kHttpTimeout));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _employees = data['employees'] ?? [];
          _loadingEmployees = false;
          _loadFailed = false;
        });
      } else {
        setState(() {
          _loadingEmployees = false;
          _loadFailed = true;
          _resultMessage = 'Failed to load employees (${response.statusCode})';
        });
      }
    } on TimeoutException {
      setState(() {
        _loadingEmployees = false;
        _loadFailed = true;
        _resultMessage = 'Server timeout - check connection';
      });
    } catch (e) {
      setState(() {
        _loadingEmployees = false;
        _loadFailed = true;
        _resultMessage = 'Connection error - check server';
      });
    }
  }

  Future<void> _capturePhoto() async {
    if (!_controller.value.isInitialized || _isCapturing) return;
    setState(() {
      _isCapturing = true;
      _resultMessage = '';
      _duplicateWarning = '';
    });

    try {
      final image = await _controller.takePicture();
      setState(() {
        _lastCapture = image;
        _isCapturing = false;
      });
      if (_selectedEmployeeId != null) {
        _checkDuplicate();
      }
    } catch (e) {
      setState(() {
        _isCapturing = false;
        _resultMessage = 'Capture failed: $e';
      });
    }
  }

  Future<void> _checkDuplicate() async {
    if (_lastCapture == null) return;
    setState(() {
      _isDuplicateCheckRunning = true;
      _duplicateWarning = '';
      _isDuplicate = false;
    });

    try {
      final bytes = await _lastCapture!.readAsBytes();
      final b64 = base64Encode(bytes);

      final response = await _sendAuthed(widget.tokenResolver, (token) => http.post(
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/faces/check-duplicate'),
        headers: _headers(token),
        body: json.encode({'image': b64, 'exclude_employee_id': _selectedEmployeeId}),
      ).timeout(kFaceRecognitionTimeout));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['duplicate'] == true) {
          setState(() {
            _isDuplicate = true;
            _duplicateWarning = 'Face already registered to: ${data['existing_employee_name']} (${data['existing_employee_code']}) — ENROLLMENT BLOCKED';
          });
        } else {
          setState(() {
            _isDuplicate = false;
            _duplicateWarning = 'Face is unique — safe to enroll';
          });
        }
      }
    } on TimeoutException {
      setState(() => _duplicateWarning = 'Duplicate check timed out');
    } catch (e) {
      setState(() => _isDuplicate = false);
    } finally {
      setState(() => _isDuplicateCheckRunning = false);
    }
  }

  Future<void> _enrollFace() async {
    if (_lastCapture == null || _selectedEmployeeId == null) return;

    if (_isDuplicate) {
      setState(() {
        _resultSuccess = false;
        _resultMessage = 'Cannot enroll — this face is already registered to another employee';
      });
      return;
    }

    setState(() {
      _isUploading = true;
      _resultMessage = '';
      _duplicateWarning = '';
    });

    try {
      final bytes = await _lastCapture!.readAsBytes();
      final b64 = base64Encode(bytes);

      final response = await _sendAuthed(widget.tokenResolver, (token) => http.post(
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/faces/enroll'),
        headers: _headers(token),
        body: json.encode({'employee_id': _selectedEmployeeId, 'image_data': b64}),
      ).timeout(kFaceRecognitionTimeout));

      if (response.statusCode == 200) {
        setState(() {
          _resultSuccess = true;
          _resultMessage = 'Face enrolled successfully for $_selectedEmployeeName!';
          _lastCapture = null;
          _duplicateWarning = '';
        });
        _fetchEmployees();
      } else {
        final body = json.decode(response.body);
        setState(() {
          _resultSuccess = false;
          _resultMessage = body['detail'] ?? 'Enrollment failed (${response.statusCode})';
        });
      }
    } on TimeoutException {
      setState(() {
        _resultSuccess = false;
        _resultMessage = 'Enrollment timed out — try again';
      });
    } catch (e) {
      setState(() {
        _resultSuccess = false;
        _resultMessage = 'Upload error: $e';
      });
    } finally {
      setState(() => _isUploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasCapture = _lastCapture != null;
    final hasEmployee = _selectedEmployeeId != null;

    return Column(
      children: [
        Expanded(
          flex: 3,
          child: Stack(
            fit: StackFit.expand,
            children: [
              FutureBuilder<void>(
                future: _initFuture,
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.done) return CameraPreview(_controller);
                  return const Center(child: CircularProgressIndicator());
                },
              ),
              Positioned(
                top: 20, left: 0, right: 0,
                child: Container(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      Text(
                        hasEmployee ? 'Enrolling: $_selectedEmployeeName' : 'Select employee first',
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        DateTime.now().toString().substring(0, 16),
                        style: const TextStyle(color: Colors.white70, fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
              Positioned(
                bottom: 20, left: 20,
                child: GestureDetector(
                  onTap: widget.onSettings,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.black.withAlpha(153), borderRadius: BorderRadius.circular(8)),
                    child: const Icon(Icons.settings, color: Colors.white70, size: 28),
                  ),
                ),
              ),
              if (!hasCapture)
                Positioned(
                  bottom: 20, left: 0, right: 0,
                  child: Center(
                    child: GestureDetector(
                      onTap: hasEmployee ? _capturePhoto : null,
                      child: Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: hasEmployee ? Colors.blue : Colors.grey,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.camera_alt, color: Colors.white, size: 36),
                      ),
                    ),
                  ),
                ),
              if (hasCapture)
                Positioned(
                  bottom: 20, left: 0, right: 0,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      GestureDetector(
                        onTap: () => setState(() {
                          _lastCapture = null;
                          _duplicateWarning = '';
                          _isDuplicate = false;
                        }),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          decoration: BoxDecoration(color: Colors.red, borderRadius: BorderRadius.circular(12)),
                          child: const Text('Retake', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(width: 20),
                      GestureDetector(
                        onTap: (_isUploading || _isDuplicate || _isDuplicateCheckRunning) ? null : _enrollFace,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          decoration: BoxDecoration(
                            color: _isDuplicate ? Colors.grey : Colors.green,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: _isUploading
                              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : Text(
                                  _isDuplicate ? 'Blocked' : 'Enroll',
                                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        if (_duplicateWarning.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            color: _isDuplicate ? Colors.red.shade100 : Colors.green.shade100,
            child: Text(
              _duplicateWarning,
              style: TextStyle(
                color: _isDuplicate ? Colors.red.shade900 : Colors.green.shade900,
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        if (_resultMessage.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            color: _resultSuccess ? Colors.green.shade100 : Colors.red.shade100,
            child: Text(
              _resultMessage,
              style: TextStyle(
                color: _resultSuccess ? Colors.green.shade900 : Colors.red.shade900,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        Expanded(
          flex: 2,
          child: _loadingEmployees
              ? const Center(child: CircularProgressIndicator())
              : _employees.isEmpty
                  ? _loadFailed
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.cloud_off, color: Colors.grey, size: 40),
                              const SizedBox(height: 8),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 24),
                                child: Text(
                                  _resultMessage.isEmpty
                                      ? 'Failed to load employees'
                                      : _resultMessage,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(color: Colors.grey),
                                ),
                              ),
                              const SizedBox(height: 12),
                              FilledButton.icon(
                                onPressed: () {
                                  setState(() {
                                    _loadingEmployees = true;
                                    _loadFailed = false;
                                  });
                                  _fetchEmployees();
                                },
                                icon: const Icon(Icons.refresh),
                                label: const Text('Retry'),
                              ),
                            ],
                          ),
                        )
                      : const Center(child: Text('No employees found. Create employees first.'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: _employees.length,
                      itemBuilder: (context, index) {
                        final emp = _employees[index];
                        final isSelected = emp['id'] == _selectedEmployeeId;
                        final isEnrolled = emp['face_enrolled'] == true;
                        return Card(
                          color: isSelected ? Colors.blue.shade50 : null,
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: isEnrolled ? Colors.green : Colors.blue,
                              child: Icon(isEnrolled ? Icons.check : Icons.person, color: Colors.white),
                            ),
                            title: Text(emp['full_name'] ?? 'Unknown'),
                            subtitle: Text(emp['employee_code'] ?? ''),
                            trailing: isEnrolled
                                ? const Chip(
                                    label: Text('Enrolled', style: TextStyle(fontSize: 11)),
                                    color: WidgetStatePropertyAll(Colors.green),
                                    visualDensity: VisualDensity.compact,
                                  )
                                : null,
                            onTap: () {
                              setState(() {
                                _selectedEmployeeId = emp['id'];
                                _selectedEmployeeName = emp['full_name'] ?? 'Unknown';
                                _lastCapture = null;
                                _resultMessage = '';
                                _duplicateWarning = '';
                                _isDuplicate = false;
                              });
                            },
                          ),
                        );
                      },
                    ),
        ),
      ],
    );
  }
}
