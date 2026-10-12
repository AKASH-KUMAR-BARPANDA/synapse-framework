import 'package:flutter/material.dart';

import 'screens/home_shell.dart';
import 'services/api_service.dart';
import 'theme/matte_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final apiService = ApiService();
  // Initialize persisted settings and sessions without blocking first frame
  apiService.initialize();
  runApp(SynapseApp(apiService: apiService));
}

class SynapseApp extends StatelessWidget {
  final ApiService apiService;

  const SynapseApp({
    super.key,
    required this.apiService,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Synapse',
      debugShowCheckedModeBanner: false,
      theme: MatteTheme.darkTheme,
      darkTheme: MatteTheme.darkTheme,
      themeMode: ThemeMode.dark,
      home: HomeShell(apiService: apiService),
    );
  }
}
