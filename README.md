# Hyouka Messages

Minimal offline Flutter SMS app with a pure-black UI.

## Real SMS

On the first launch after installation, Hyouka Messages asks Android to make it the default SMS application through the SMS role. The prompt is only auto-triggered once; a manual "Set Hyouka Messages as the default SMS app" action remains available if the user declines.

When the app is the default SMS app and the required Android SMS permissions are available, it reads real SMS conversations from the system SMS provider.

A normal tap on any conversation opens its full message thread. Opening a thread marks its messages as read.

Long-pressing a conversation opens Delete / Cancel confirmation and deletes that real SMS conversation from the phone when confirmed.

The "Select all" action is the bulk-delete entry point: it confirms once and deletes all SMS messages in one operation.

Incoming SMS is received through Android's SMS_DELIVER broadcast and inserted into the SMS inbox provider so the new message becomes visible to the app.

## Android default SMS role

Android's ROLE_SMS requires SMS delivery receivers plus SENDTO and RESPOND_VIA_MESSAGE handling. The build script configures these native Android components on every GitHub Actions build.

MMS UI and sending are intentionally not implemented in this minimal version.

## Privacy

SMS is sensitive user data. The app has no network data source and no runtime network dependency.
