import 'package:flutter_test/flutter_test.dart';
import 'package:hyouka_messages/main.dart';

void main() {
  testWidgets('shows the messages list and select all action', (tester) async {
    await tester.pumpWidget(const MessagesApp());

    expect(find.text('Messages'), findsOneWidget);
    expect(find.text('Hyouka'), findsOneWidget);
    expect(find.text('Select all'), findsOneWidget);
  });

  testWidgets('long press opens delete or cancel confirmation', (tester) async {
    await tester.pumpWidget(const MessagesApp());

    await tester.longPress(find.text('Hyouka'));
    await tester.pumpAndSettle();

    expect(find.text('Delete this message?'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
    expect(find.text('Delete'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('cancel-delete')));
    await tester.pumpAndSettle();

    expect(find.text('Hyouka'), findsOneWidget);
  });

  testWidgets('select all enables one-step bulk delete confirmation', (tester) async {
    await tester.pumpWidget(const MessagesApp());

    await tester.tap(find.byKey(const ValueKey('select-all')));
    await tester.pumpAndSettle();

    expect(find.text('5 selected'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('delete-selected')));
    await tester.pumpAndSettle();

    expect(find.text('Delete 5 messages?'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('confirm-delete')));
    await tester.pumpAndSettle();

    expect(find.text('No messages'), findsOneWidget);
  });
}
