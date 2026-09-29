import 'package:flutter/material.dart';

void main() {
  runApp(const MessagesApp());
}

class Message {
  const Message({
    required this.id,
    required this.sender,
    required this.preview,
    required this.time,
    this.unread = false,
  });

  final int id;
  final String sender;
  final String preview;
  final String time;
  final bool unread;
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
          backgroundColor: Color(0xFF161616),
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

class _MessagesScreenState extends State<MessagesScreen> {
  final List<Message> _messages = const [
    Message(
      id: 1,
      sender: 'Hyouka',
      preview: 'See you later.',
      time: '9:18 PM',
      unread: true,
    ),
    Message(
      id: 2,
      sender: 'Alex',
      preview: 'The file is ready.',
      time: '8:42 PM',
    ),
    Message(
      id: 3,
      sender: 'Mina',
      preview: 'Thanks!',
      time: '7:30 PM',
    ),
    Message(
      id: 4,
      sender: 'Omar',
      preview: 'Can you call me?',
      time: '6:05 PM',
      unread: true,
    ),
    Message(
      id: 5,
      sender: 'Noor',
      preview: 'Got it.',
      time: 'Yesterday',
    ),
  ].toList();

  final Set<int> _selectedIds = <int>{};

  bool get _selectionMode => _selectedIds.isNotEmpty;

  void _toggleSelected(int id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
  }

  void _selectAll() {
    setState(() {
      _selectedIds
        ..clear()
        ..addAll(_messages.map((message) => message.id));
    });
  }

  void _clearSelection() {
    setState(_selectedIds.clear);
  }

  Future<void> _confirmDelete({
    required List<Message> targets,
    required bool bulk,
  }) async {
    if (targets.isEmpty) return;

    final title = bulk
        ? 'Delete ${targets.length} messages?'
        : 'Delete this message?';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(
          bulk
              ? 'This will remove the selected messages from this app.'
              : 'This message will be removed from this app.',
        ),
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

    if (confirmed != true || !mounted) return;

    setState(() {
      final ids = targets.map((message) => message.id).toSet();
      _messages.removeWhere((message) => ids.contains(message.id));
      _selectedIds.removeWhere(ids.contains);
    });
  }

  Future<void> _handleLongPress(Message message) async {
    if (_selectionMode) {
      _toggleSelected(message.id);
      return;
    }

    await _confirmDelete(targets: [message], bulk: false);
  }

  Future<void> _deleteSelected() async {
    final targets = _messages
        .where((message) => _selectedIds.contains(message.id))
        .toList();
    await _confirmDelete(targets: targets, bulk: true);
  }

  @override
  Widget build(BuildContext context) {
    final title = _selectionMode
        ? '${_selectedIds.length} selected'
        : 'Messages';

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        titleSpacing: 20,
        title: Text(
          title,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.6,
          ),
        ),
        actions: [
          if (_selectionMode) ...[
            TextButton(
              key: const ValueKey('select-all'),
              onPressed: _selectAll,
              child: const Text('Select all'),
            ),
            IconButton(
              key: const ValueKey('delete-selected'),
              tooltip: 'Delete selected',
              onPressed: _deleteSelected,
              icon: const Icon(Icons.delete_outline, color: Colors.white),
            ),
            IconButton(
              key: const ValueKey('cancel-selection'),
              tooltip: 'Cancel selection',
              onPressed: _clearSelection,
              icon: const Icon(Icons.close, color: Colors.white),
            ),
            const SizedBox(width: 8),
          ] else ...[
            TextButton(
              key: const ValueKey('select-all'),
              onPressed: _selectAll,
              child: const Text('Select all'),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
      body: _messages.isEmpty
          ? const _EmptyMessages()
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
              itemCount: _messages.length,
              separatorBuilder: (_, __) => const SizedBox(height: 2),
              itemBuilder: (context, index) {
                final message = _messages[index];
                final selected = _selectedIds.contains(message.id);

                return MessageTile(
                  message: message,
                  selected: selected,
                  onTap: _selectionMode
                      ? () => _toggleSelected(message.id)
                      : () {},
                  onLongPress: () => _handleLongPress(message),
                );
              },
            ),
    );
  }
}

class MessageTile extends StatelessWidget {
  const MessageTile({
    required this.message,
    required this.selected,
    required this.onTap,
    required this.onLongPress,
    super.key,
  });

  final Message message;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFF1A1A1A) : Colors.black,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        onLongPress: onLongPress,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: const Color(0xFF242424),
                child: Text(
                  message.sender.characters.first.toUpperCase(),
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
                            message.sender,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: message.unread
                                  ? FontWeight.w700
                                  : FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          message.time,
                          style: const TextStyle(
                            color: Color(0xFF8A8A8A),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      message.preview,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF9D9D9D),
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected) ...[
                const SizedBox(width: 10),
                const Icon(Icons.check_circle, color: Colors.white),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyMessages extends StatelessWidget {
  const _EmptyMessages();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        'No messages',
        style: TextStyle(
          color: Color(0xFF8A8A8A),
          fontSize: 16,
        ),
      ),
    );
  }
}
