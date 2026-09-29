import 'package:flutter_test/flutter_test.dart';
import 'package:hyouka_messages/main.dart';

void main() {
  testWidgets('renders the Messages screen', (tester) async {
    await tester.pumpWidget(const MessagesApp());

    expect(find.text('Messages'), findsOneWidget);
  });

  testWidgets('conversation screen renders an opened SMS thread',
      (tester) async {
    final messages = [
      SmsItem(
        id: 1,
        address: '+201000000000',
        body: 'Hello',
        date: DateTime(2026, 9, 29, 20, 30),
        type: 1,
        read: true,
      ),
      SmsItem(
        id: 2,
        address: '+201000000000',
        body: 'Reply',
        date: DateTime(2026, 9, 29, 20, 31),
        type: 2,
        read: true,
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: ConversationScreen(
          threadId: 7,
          address: '+201000000000',
          messages: messages,
        ),
      ),
    );

    expect(find.text('+201000000000'), findsOneWidget);
    expect(find.text('Hello'), findsOneWidget);
    expect(find.text('Reply'), findsOneWidget);
  });
}
