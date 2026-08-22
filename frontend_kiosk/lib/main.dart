import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:io';

const String kApiPrefix = '/api/v1';
const String kDefaultIp = '192.168.1.8';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (kIsWeb) {
    final cameras = await availableCameras();
    runApp(MyApp(cameras: cameras, serverIp: ''));
  } else {
    final cameras = await availableCameras();
    final prefs = await SharedPreferences.getInstance();
    final savedIp = prefs.getString('server_ip') ?? kDefaultIp;
    runApp(MyApp(cameras: cameras, serverIp: savedIp));
  }
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
      home: KioskScreen(cameras: cameras, serverIp: serverIp),
      debugShowCheckedModeBanner: false,
    );
  }
}

class KioskScreen extends StatefulWidget {
  final List<CameraDescription> cameras;
  final String serverIp;

  const KioskScreen({super.key, required this.cameras, required this.serverIp});

  @override
  State<KioskScreen> createState() => _KioskScreenState();
}

class _KioskScreenState extends State<KioskScreen> {
  late CameraController _controller;
  late Future<void> _initializeControllerFuture;
  String _status = 'Initializing...';
  String _employeeName = '';
  String _employeeCode = '';
  bool _isProcessing = false;
  String? _authToken;
  int _recognitionCount = 0;
  int _currentCameraIndex = 0;
  late String _serverIp;

  String get kApiBaseUrl {
    if (kIsWeb) {
      final origin = Uri.base.origin;
      return origin;
    }
    return 'http://$_serverIp:8080';
  }

  @override
  void initState() {
    super.initState();
    _serverIp = widget.serverIp;
    _initCamera(widget.cameras[_currentCameraIndex]);
    _login();
  }

  void _initCamera(CameraDescription camera) {
    _controller = CameraController(
      camera,
      ResolutionPreset.high,
      enableAudio: false,
    );
    _initializeControllerFuture = _controller.initialize();
  }

  Future<void> _switchCamera() async {
    if (widget.cameras.length < 2) return;
    await _controller.dispose();
    _currentCameraIndex = (_currentCameraIndex + 1) % widget.cameras.length;
    setState(() {
      _initCamera(widget.cameras[_currentCameraIndex]);
    });
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
            labelText: 'Server IP Address',
            hintText: 'e.g. 192.168.1.8',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.number,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final newIp = controller.text.trim();
              if (newIp.isNotEmpty) {
                final prefs = await SharedPreferences.getInstance();
                await prefs.setString('server_ip', newIp);
                setState(() {
                  _serverIp = newIp;
                  _status = 'Connecting to $newIp...';
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
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    try {
      final response = await http.post(
        Uri.parse('$kApiBaseUrl$kApiPrefix/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': 'admin@smartface.com',
          'password': 'Admin123!',
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _authToken = data['access_token'];
        setState(() {
          _status = 'Ready for attendance';
        });
        _startContinuousDetection();
      } else {
        setState(() {
          _status = 'Auth failed: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _status = 'Server unreachable. Check connection.';
      });
      await Future.delayed(const Duration(seconds: 5));
      _login();
    }
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<void> _startContinuousDetection() async {
    while (mounted) {
      if (!_isProcessing) {
        await _captureAndRecognize();
      }
      await Future.delayed(const Duration(seconds: 2));
    }
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

      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$kApiBaseUrl$kApiPrefix/faces/recognize'),
      );
      if (_authToken != null) {
        request.headers['Authorization'] = 'Bearer $_authToken';
      }
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: 'capture.jpg',
        ),
      );

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        if (data['recognized'] == true) {
          final employeeId = data['employee_id'] ?? '';
          final name = data['employee_name'] ?? 'Unknown';
          final code = data['employee_code'] ?? '';
          final confidence = data['confidence'] ?? 0;

          setState(() {
            _employeeName = name;
            _employeeCode = code;
            _status = 'CHECK-IN SUCCESS';
            _recognitionCount++;
          });

          await _recordAttendance(employeeId, confidence);

          await Future.delayed(const Duration(seconds: 3));

          setState(() {
            _status = 'Ready for attendance';
            _employeeName = '';
            _employeeCode = '';
          });
        } else {
          setState(() {
            _status = 'FACE NOT RECOGNIZED';
          });

          await Future.delayed(const Duration(seconds: 2));

          setState(() {
            _status = 'Ready for attendance';
          });
        }
      } else if (response.statusCode == 401) {
        setState(() {
          _status = 'Session expired. Reconnecting...';
        });
        await _login();
      } else {
        setState(() {
          _status = 'Error ${response.statusCode}';
        });
        await Future.delayed(const Duration(seconds: 2));
        setState(() {
          _status = 'Ready for attendance';
        });
      }
    } catch (e) {
      setState(() {
        _status = 'Connection error';
      });
      await Future.delayed(const Duration(seconds: 3));
      setState(() {
        _status = 'Ready for attendance';
      });
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _recordAttendance(String employeeId, double confidence) async {
    try {
      final response = await http.post(
        Uri.parse('$kApiBaseUrl$kApiPrefix/attendance/checkin'),
        headers: _headers,
        body: json.encode({
          'employee_id': employeeId,
          'confidence_score': confidence,
        }),
      );

      if (response.statusCode != 200) {
        debugPrint('Attendance record failed: ${response.body}');
      }
    } catch (e) {
      debugPrint('Attendance error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<void>(
            future: _initializeControllerFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.done) {
                return CameraPreview(_controller);
              } else {
                return const Center(
                  child: CircularProgressIndicator(color: Colors.white),
                );
              }
            },
          ),

          Container(
            decoration: BoxDecoration(
              border: Border.all(
                color: _status == 'CHECK-IN SUCCESS'
                    ? Colors.green
                    : _status == 'FACE NOT RECOGNIZED'
                        ? Colors.red
                        : Colors.blue,
                width: 4,
              ),
            ),
          ),

          Positioned(
            top: 50,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  const Text(
                    'SMARTFACE',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    _status,
                    style: TextStyle(
                      color: _status == 'CHECK-IN SUCCESS'
                          ? Colors.green
                          : _status == 'FACE NOT RECOGNIZED'
                              ? Colors.red
                              : Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    DateTime.now().toString().substring(0, 16),
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            ),
          ),

          if (_employeeName.isNotEmpty)
            Positioned(
              bottom: 100,
              left: 0,
              right: 0,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 40),
                padding: const EdgeInsets.all(30),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.check_circle,
                      color: Colors.green,
                      size: 80,
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      'WELCOME',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _employeeName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                      ),
                    ),
                    if (_employeeCode.isNotEmpty)
                      Text(
                        _employeeCode,
                        style: const TextStyle(
                          color: Colors.grey,
                          fontSize: 16,
                        ),
                      ),
                    const SizedBox(height: 10),
                    Text(
                      DateTime.now().toString().substring(11, 16),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                      ),
                    ),
                  ],
                ),
              ),
            ),

          if (_status == 'FACE NOT RECOGNIZED')
            Positioned(
              bottom: 100,
              left: 0,
              right: 0,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 40),
                padding: const EdgeInsets.all(30),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Column(
                  children: [
                    Icon(
                      Icons.error_outline,
                      color: Colors.red,
                      size: 80,
                    ),
                    SizedBox(height: 20),
                    Text(
                      'FACE NOT RECOGNIZED',
                      style: TextStyle(
                        color: Colors.red,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 10),
                    Text(
                      'PLEASE CONTACT HR',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                      ),
                    ),
                  ],
                ),
              ),
            ),

          Positioned(
            bottom: 30,
            right: 30,
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Scans: $_recognitionCount',
                    style: const TextStyle(color: Colors.white70, fontSize: 14),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: _switchCamera,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.cameraswitch,
                      color: Colors.white70,
                      size: 28,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: _showSettings,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.settings,
                      color: Colors.white70,
                      size: 28,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
