import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const _smsChannel = MethodChannel('hyouka.messages/sms');

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MessagesApp());
}

class SmsConversation {
  const SmsConversation({
    required this.threadId,
    required this.address,
    required this.preview,
    required this.date,
    required this.messageCount,
    required this.unread,
  });

  final int threadId;
  final String address;
  final String preview;
  final DateTime date;
  final int messageCount;
  final bool unread;
}

class SmsItem {
  const SmsItem({
    required this.id,
    required this.address,
    required this.body,
    required this.date,
    required this.type,
    required this.read,
  });

  final int id;
  final String address;
  final String body;
  final DateTime date;
  final int type;
  final bool read;

  bool get outgoing => type == 2;
}

class MessagesApp extends StatelessWidget {
  const MessagesApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Colors.black,
        canvasColor: Colors.black,
        colorScheme: const ColorScheme.dark(
          surface: Colors.black,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
          elevation: 0,
          surfaceTintColor: Colors.transparent,
        ),
        dialogTheme: const DialogThemeData(
          backgroundColor: Color(0xFF151515),
          surfaceTintColor: Colors.transparent,
        ),
      ),
      home: const MessagesScreen(),
    );
  }
}

class MessagesScreen extends StatefulWidget {
  const MessagesScreen({super.key});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen>
    with WidgetsBindingObserver {
  List<SmsConversation> _conversations = const [];
  bool _loading = true;
  bool _isDefault = false;
  bool _defaultPromptedThisLaunch = false;
  bool _permissionsRequestedThisLaunch = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _prepare();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _prepare();
    }
  }

  Future<void> _prepare() async {
    try {
      final defaultApp =
          await _smsChannel.invokeMethod<bool>('isDefaultSmsApp') ?? false;

      if (!mounted) return;

      setState(() {
        _isDefault = defaultApp;
        _error = null;
      });

      if (!defaultApp) {
        if (!_defaultPromptedThisLaunch) {
          _defaultPromptedThisLaunch = true;
          await _smsChannel.invokeMethod('requestDefaultSmsApp');
        }
        return;
      }

      if (!_permissionsRequestedThisLaunch) {
        _permissionsRequestedThisLaunch = true;
        final allGranted =
            await _smsChannel.invokeMethod<bool>('requestSmsPermissions') ??
                false;
        if (!allGranted) return;
      }

      await _loadConversations();
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.message ?? 'SMS access is unavailable.';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _requestDefault() async {
    try {
      await _smsChannel.invokeMethod('requestDefaultSmsApp');
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message ?? 'Unable to open the default SMS prompt.';
      });
    }
  }

  Future<void> _loadConversations() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final raw = await _smsChannel.invokeMethod<List<dynamic>>(
        'getConversations',
      );

      final conversations = (raw ?? const <dynamic>[])
          .map(
            (entry) => SmsConversation(
              threadId: (entry['threadId'] as num).toInt(),
              address: (entry['address'] as String?) ?? 'Unknown',
              preview: (entry['preview'] as String?) ?? '',
              date: DateTime.fromMillisecondsSinceEpoch(
                (entry['date'] as num).toInt(),
              ),
              messageCount: (entry['messageCount'] as num).toInt(),
              unread: entry['unread'] == true,
            ),
          )
          .toList();

      if (!mounted) return;
      setState(() {
        _conversations = conversations;
        _loading = false;
      });
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.message ?? 'Unable to read SMS messages.';
      });
    }
  }

  Future<List<SmsItem>> _loadThread(int threadId) async {
    final raw = await _smsChannel.invokeMethod<List<dynamic>>(
      'getThreadMessages',
      <String, dynamic>{'threadId': threadId},
    );

    return (raw ?? const <dynamic>[])
        .map(
          (entry) => SmsItem(
            id: (entry['id'] as num).toInt(),
            address: (entry['address'] as String?) ?? 'Unknown',
            body: (entry['body'] as String?) ?? '',
            date: DateTime.fromMillisecondsSinceEpoch(
              (entry['date'] as num).toInt(),
            ),
            type: (entry['type'] as num).toInt(),
            read: entry['read'] == true,
          ),
        )
        .toList();
  }

  Future<void> _deleteConversation(SmsConversation conversation) async {
    final confirmed = await _confirmDelete(
      title: 'Delete conversation?',
      content:
          'This will permanently delete this SMS conversation from the phone.',
    );
    if (confirmed != true) return;

    try {
      await _smsChannel.invokeMethod(
        'deleteThread',
        <String, dynamic>{'threadId': conversation.threadId},
      );
      await _loadConversations();
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message ?? 'Unable to delete the conversation.';
      });
    }
  }

  Future<void> _deleteAll() async {
    if (_conversations.isEmpty) return;

    final confirmed = await _confirmDelete(
      title: 'Delete all messages?',
      content:
          'This will permanently delete all SMS messages stored on the phone.',
    );
    if (confirmed != true) return;

    try {
      await _smsChannel.invokeMethod('deleteAllMessages');
      await _loadConversations();
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message ?? 'Unable to delete all SMS messages.';
      });
    }
  }

  Future<bool?> _confirmDelete({
    required String title,
    required String content,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(content),
        actions: [
          TextButton(
            key: const ValueKey('cancel-delete'),
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            key: const ValueKey('confirm-delete'),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    if (date.year == now.year &&
        date.month == now.month &&
        date.day == now.day) {
      final hour = date.hour % 12 == 0 ? 12 : date.hour % 12;
      final minute = date.minute.toString().padLeft(2, '0');
      final suffix = date.hour >= 12 ? 'PM' : 'AM';
      return hour.toString() + ':' + minute + ' ' + suffix;
    }
    if (date.year == now.year) {
      return date.day.toString() + '/' + date.month.toString();
    }
    return date.day.toString() +
        '/' +
        date.month.toString() +
        '/' +
        date.year.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        titleSpacing: 20,
        title: const Text(
          'Messages',
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.6,
          ),
        ),
        actions: [
          if (_conversations.isNotEmpty)
            TextButton(
              key: const ValueKey('select-all'),
              onPressed: _deleteAll,
              child: const Text('Select all'),
            ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          if (!_isDefault)
            Material(
              color: const Color(0xFF111111),
              child: InkWell(
                onTap: _requestDefault,
                child: const Padding(
                  padding: EdgeInsets.fromLTRB(20, 12, 14, 12),
                  child: Row(
                    children: [
                      Icon(
                        Icons.message_outlined,
                        color: Colors.white,
                        size: 20,
                      ),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Set Hyouka Messages as the default SMS app',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Icon(
                        Icons.chevron_right,
                        color: Color(0xFF8A8A8A),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: Color(0xFFBDBDBD),
                  fontSize: 13,
                ),
              ),
            ),
          Expanded(
            child: _loading
                ? const Center(
                    child: SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : _conversations.isEmpty
                    ? const Center(
                        child: Text(
                          'No messages',
                          style: TextStyle(
                            color: Color(0xFF8A8A8A),
                            fontSize: 16,
                          ),
                        ),
                      )
                    : RefreshIndicator(
                        backgroundColor: const Color(0xFF151515),
                        onRefresh: _loadConversations,
                        child: ListView.separated(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
                          itemCount: _conversations.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 2),
                          itemBuilder: (context, index) {
                            final conversation = _conversations[index];
                            return _ConversationTile(
                              conversation: conversation,
                              time: _formatDate(conversation.date),
                              onTap: () async {
                                if (!_isDefault) {
                                  await _requestDefault();
                                  return;
                                }

                                final messages =
                                    await _loadThread(conversation.threadId);
                                if (!context.mounted) return;

                                await Navigator.of(context).push(
                                  MaterialPageRoute<void>(
                                    builder: (_) => ConversationScreen(
                                      threadId: conversation.threadId,
                                      address: conversation.address,
                                      messages: messages,
                                    ),
                                  ),
                                );

                                await _loadConversations();
                              },
                              onLongPress: () =>
                                  _deleteConversation(conversation),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _ConversationTile extends StatelessWidget {
  const _ConversationTile({
    required this.conversation,
    required this.time,
    required this.onTap,
    required this.onLongPress,
  });

  final SmsConversation conversation;
  final String time;
  final VoidCallback onTap;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    final firstCharacter = conversation.address.isEmpty
        ? '?'
        : conversation.address.characters.first;

    return Material(
      color: Colors.black,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        onLongPress: onLongPress,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: const Color(0xFF242424),
                child: Text(
                  firstCharacter,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            conversation.address,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: conversation.unread
                                  ? FontWeight.w700
                                  : FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          time,
                          style: const TextStyle(
                            color: Color(0xFF8A8A8A),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      conversation.preview,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: const Color(0xFF9D9D9D),
                        fontSize: 14,
                        fontWeight: conversation.unread
                            ? FontWeight.w600
                            : FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ConversationScreen extends StatelessWidget {
  const ConversationScreen({
    required this.threadId,
    required this.address,
    required this.messages,
    super.key,
  });

  final int threadId;
  final String address;
  final List<SmsItem> messages;

  String _formatTime(DateTime date) {
    final hour = date.hour % 12 == 0 ? 12 : date.hour % 12;
    final minute = date.minute.toString().padLeft(2, '0');
    final suffix = date.hour >= 12 ? 'PM' : 'AM';
    return hour.toString() + ':' + minute + ' ' + suffix;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        titleSpacing: 0,
        title: Text(
          address,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: ListView.builder(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 28),
        itemCount: messages.length,
        itemBuilder: (context, index) {
          final message = messages[index];

          return Align(
            alignment: message.outgoing
                ? Alignment.centerRight
                : Alignment.centerLeft,
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.sizeOf(context).width * 0.80,
              ),
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
              decoration: BoxDecoration(
                color: message.outgoing
                    ? const Color(0xFF1F1F1F)
                    : const Color(0xFF141414),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.body,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _formatTime(message.date),
                    style: const TextStyle(
                      color: Color(0xFF858585),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
