import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

const String kApiPrefix = '/api/v1';
const String kDefaultUrl = 'https://smartface-attendance-7ygu.onrender.com';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final cameras = await availableCameras();
  final prefs = await SharedPreferences.getInstance();
  final savedIp = kIsWeb ? '' : (prefs.getString('server_ip') ?? kDefaultUrl);
  runApp(MyApp(cameras: cameras, serverIp: savedIp));
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
  }

  Future<void> _login() async {
    try {
      final response = await http.post(
        Uri.parse('$kApiBaseUrl$kApiPrefix/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': 'admin@smartface.com', 'password': 'Admin123!'}),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _authToken = data['access_token'];
        setState(() {});
      }
    } catch (e) {
      debugPrint('Login failed: $e');
    }
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
                });
                Navigator.pop(context);
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
      body: _currentMode == 0
          ? AttendanceMode(
              key: ValueKey('att_$_serverIp'),
              cameras: widget.cameras,
              apiBaseUrl: kApiBaseUrl,
              authToken: _authToken,
              onSettings: _showSettings,
            )
          : EnrollmentMode(
              key: ValueKey('enr_$_serverIp'),
              cameras: widget.cameras,
              apiBaseUrl: kApiBaseUrl,
              authToken: _authToken,
              onSettings: _showSettings,
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
  final String? authToken;
  final VoidCallback onSettings;
  const AttendanceMode({
    super.key,
    required this.cameras,
    required this.apiBaseUrl,
    required this.authToken,
    required this.onSettings,
  });

  @override
  State<AttendanceMode> createState() => _AttendanceModeState();
}

class _AttendanceModeState extends State<AttendanceMode> {
  late CameraController _controller;
  late Future<void> _initFuture;
  String _status = 'Initializing...';
  String _employeeName = '';
  String _employeeCode = '';
  bool _isProcessing = false;
  int _recognitionCount = 0;
  int _camIdx = 0;

  @override
  void initState() {
    super.initState();
    _initCamera(widget.cameras[_camIdx]);
  }

  void _initCamera(CameraDescription cam) {
    _controller = CameraController(cam, ResolutionPreset.high, enableAudio: false);
    _initFuture = _controller.initialize();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _switchCamera() async {
    if (widget.cameras.length < 2) return;
    await _controller.dispose();
    _camIdx = (_camIdx + 1) % widget.cameras.length;
    setState(() => _initCamera(widget.cameras[_camIdx]));
  }

  Future<void> _captureAndRecognize() async {
    if (!_controller.value.isInitialized || _isProcessing) return;
    setState(() {
      _isProcessing = true;
      _status = 'Detecting face...';
    });

    try {
      final XFile image = await _controller.takePicture();
      final bytes = await image.readAsBytes();

      var req = http.MultipartRequest('POST', Uri.parse('${widget.apiBaseUrl}$kApiPrefix/faces/recognize'));
      if (widget.authToken != null) req.headers['Authorization'] = 'Bearer ${widget.authToken}';
      req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: 'capture.jpg'));

      var res = await req.send();
      var response = await http.Response.fromStream(res);

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
            _recognitionCount++;
          });

          await http.post(
            Uri.parse('${widget.apiBaseUrl}$kApiPrefix/attendance/checkin'),
            headers: {'Content-Type': 'application/json', if (widget.authToken != null) 'Authorization': 'Bearer ${widget.authToken}'},
            body: json.encode({'employee_id': employeeId, 'confidence_score': confidence}),
          );

          await Future.delayed(const Duration(seconds: 3));
          setState(() { _status = 'Ready for attendance'; _employeeName = ''; _employeeCode = ''; });
        } else {
          setState(() => _status = 'FACE NOT RECOGNIZED');
          await Future.delayed(const Duration(seconds: 2));
          setState(() => _status = 'Ready for attendance');
        }
      } else {
        setState(() => _status = 'Error ${response.statusCode}');
        await Future.delayed(const Duration(seconds: 2));
        setState(() => _status = 'Ready for attendance');
      }
    } catch (e) {
      setState(() => _status = 'Connection error');
      await Future.delayed(const Duration(seconds: 3));
      setState(() => _status = 'Ready for attendance');
    } finally {
      setState(() => _isProcessing = false);
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
              color: _status == 'CHECK-IN SUCCESS' ? Colors.green : _status == 'FACE NOT RECOGNIZED' ? Colors.red : Colors.blue,
              width: 4,
            ),
          ),
        ),
        Positioned(
          top: 50, left: 0, right: 0,
          child: Column(children: [
            const Text('SMARTFACE', style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text(_status, style: TextStyle(
              color: _status == 'CHECK-IN SUCCESS' ? Colors.green : _status == 'FACE NOT RECOGNIZED' ? Colors.red : Colors.white,
              fontSize: 24, fontWeight: FontWeight.bold,
            )),
            const SizedBox(height: 5),
            Text(DateTime.now().toString().substring(0, 16), style: const TextStyle(color: Colors.white70, fontSize: 16)),
          ]),
        ),
        if (_employeeName.isNotEmpty)
          Positioned(
            bottom: 100, left: 40, right: 40,
            child: Container(
              padding: const EdgeInsets.all(30),
              decoration: BoxDecoration(color: Colors.black.withAlpha(204), borderRadius: BorderRadius.circular(20)),
              child: Column(children: [
                const Icon(Icons.check_circle, color: Colors.green, size: 80),
                const SizedBox(height: 20),
                const Text('WELCOME', style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 10),
                Text(_employeeName, style: const TextStyle(color: Colors.white, fontSize: 24)),
                if (_employeeCode.isNotEmpty) Text(_employeeCode, style: const TextStyle(color: Colors.grey, fontSize: 16)),
                const SizedBox(height: 10),
                Text(DateTime.now().toString().substring(11, 16), style: const TextStyle(color: Colors.white, fontSize: 20)),
              ]),
            ),
          ),
        if (_status == 'FACE NOT RECOGNIZED')
          Positioned(
            bottom: 100, left: 40, right: 40,
            child: Container(
              padding: const EdgeInsets.all(30),
              decoration: BoxDecoration(color: Colors.black.withAlpha(204), borderRadius: BorderRadius.circular(20)),
              child: const Column(children: [
                Icon(Icons.error_outline, color: Colors.red, size: 80),
                SizedBox(height: 20),
                Text('FACE NOT RECOGNIZED', style: TextStyle(color: Colors.red, fontSize: 24, fontWeight: FontWeight.bold)),
                SizedBox(height: 10),
                Text('PLEASE CONTACT HR', style: TextStyle(color: Colors.white, fontSize: 18)),
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
              onTap: _switchCamera,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: Colors.black.withAlpha(153), borderRadius: BorderRadius.circular(8)),
                child: const Icon(Icons.cameraswitch, color: Colors.white70, size: 28),
              ),
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
        Positioned(
          bottom: 30, left: 30,
          child: GestureDetector(
            onTap: () async {
              if (!_controller.value.isInitialized) return;
              await _captureAndRecognize();
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.blue.withAlpha(200), borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.camera_alt, color: Colors.white, size: 32),
            ),
          ),
        ),
      ],
    );
  }
}

class EnrollmentMode extends StatefulWidget {
  final List<CameraDescription> cameras;
  final String apiBaseUrl;
  final String? authToken;
  final VoidCallback onSettings;
  const EnrollmentMode({
    super.key,
    required this.cameras,
    required this.apiBaseUrl,
    required this.authToken,
    required this.onSettings,
  });

  @override
  State<EnrollmentMode> createState() => _EnrollmentModeState();
}

class _EnrollmentModeState extends State<EnrollmentMode> {
  late CameraController _controller;
  late Future<void> _initFuture;
  int _camIdx = 0;
  List<dynamic> _employees = [];
  String? _selectedEmployeeId;
  String _selectedEmployeeName = '';
  bool _loadingEmployees = true;
  bool _isCapturing = false;
  bool _isUploading = false;
  String _resultMessage = '';
  bool _resultSuccess = false;
  XFile? _lastCapture;

  @override
  void initState() {
    super.initState();
    _initCamera(widget.cameras[_camIdx]);
    _fetchEmployees();
  }

  void _initCamera(CameraDescription cam) {
    _controller = CameraController(cam, ResolutionPreset.high, enableAudio: false);
    _initFuture = _controller.initialize();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _switchCamera() async {
    if (widget.cameras.length < 2) return;
    await _controller.dispose();
    _camIdx = (_camIdx + 1) % widget.cameras.length;
    setState(() => _initCamera(widget.cameras[_camIdx]));
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (widget.authToken != null) 'Authorization': 'Bearer ${widget.authToken}',
  };

  Future<void> _fetchEmployees() async {
    try {
      final response = await http.get(
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/employees?limit=200'),
        headers: _headers,
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _employees = data['employees'] ?? [];
          _loadingEmployees = false;
        });
      } else {
        setState(() { _loadingEmployees = false; _resultMessage = 'Failed to load employees'; });
      }
    } catch (e) {
      setState(() { _loadingEmployees = false; _resultMessage = 'Connection error'; });
    }
  }

  Future<void> _capturePhoto() async {
    if (!_controller.value.isInitialized || _isCapturing) return;
    setState(() { _isCapturing = true; _resultMessage = ''; });

    try {
      final image = await _controller.takePicture();
      setState(() { _lastCapture = image; _isCapturing = false; });
    } catch (e) {
      setState(() { _isCapturing = false; _resultMessage = 'Capture failed: $e'; });
    }
  }

  Future<void> _enrollFace() async {
    if (_lastCapture == null || _selectedEmployeeId == null) return;
    setState(() { _isUploading = true; _resultMessage = ''; });

    try {
      final bytes = await _lastCapture!.readAsBytes();
      var req = http.MultipartRequest(
        'POST',
        Uri.parse('${widget.apiBaseUrl}$kApiPrefix/faces/enroll?employee_id=$_selectedEmployeeId'),
      );
      if (widget.authToken != null) req.headers['Authorization'] = 'Bearer ${widget.authToken}';
      req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: 'face.jpg'));

      var res = await req.send();
      var response = await http.Response.fromStream(res);

      if (response.statusCode == 200) {
        setState(() {
          _resultSuccess = true;
          _resultMessage = 'Face enrolled successfully for $_selectedEmployeeName!';
          _lastCapture = null;
        });
      } else {
        final body = json.decode(response.body);
        setState(() {
          _resultSuccess = false;
          _resultMessage = body['detail'] ?? 'Enrollment failed (${response.statusCode})';
        });
      }
    } catch (e) {
      setState(() { _resultSuccess = false; _resultMessage = 'Upload error: $e'; });
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
                bottom: 20, right: 20,
                child: GestureDetector(
                  onTap: _switchCamera,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.black.withAlpha(153), borderRadius: BorderRadius.circular(8)),
                    child: const Icon(Icons.cameraswitch, color: Colors.white70, size: 28),
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
                        onTap: () => setState(() => _lastCapture = null),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          decoration: BoxDecoration(color: Colors.red, borderRadius: BorderRadius.circular(12)),
                          child: const Text('Retake', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(width: 20),
                      GestureDetector(
                        onTap: _isUploading ? null : _enrollFace,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          decoration: BoxDecoration(color: Colors.green, borderRadius: BorderRadius.circular(12)),
                          child: _isUploading
                              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : const Text('Enroll', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        if (_resultMessage.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            color: _resultSuccess ? Colors.green.shade100 : Colors.red.shade100,
            child: Text(
              _resultMessage,
              style: TextStyle(color: _resultSuccess ? Colors.green.shade900 : Colors.red.shade900, fontSize: 16, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
        Expanded(
          flex: 2,
          child: _loadingEmployees
              ? const Center(child: CircularProgressIndicator())
              : _employees.isEmpty
                  ? const Center(child: Text('No employees found. Create employees first.'))
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
                                ? const Chip(label: Text('Enrolled', style: TextStyle(fontSize: 11)), color: WidgetStatePropertyAll(Colors.green), visualDensity: VisualDensity.compact)
                                : null,
                            onTap: () {
                              setState(() {
                                _selectedEmployeeId = emp['id'];
                                _selectedEmployeeName = emp['full_name'] ?? 'Unknown';
                                _lastCapture = null;
                                _resultMessage = '';
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
