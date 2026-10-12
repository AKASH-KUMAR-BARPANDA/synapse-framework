import 'package:flutter_test/flutter_test.dart';
import 'package:synapse_ui/main.dart';
import 'package:synapse_ui/services/api_service.dart';

void main() {
  testWidgets('SynapseApp renders HomeShell smoke test', (
    WidgetTester tester,
  ) async {
    final apiService = ApiService();
    await tester.pumpWidget(SynapseApp(apiService: apiService));

    expect(find.text('Synapse Personal Intelligence'), findsOneWidget);
  });
}
