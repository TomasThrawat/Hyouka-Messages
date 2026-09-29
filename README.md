# Hyouka Messages

Minimal offline Flutter SMS app with a pure-black UI.

## Real SMS behavior

- On first launch, the app requests the Android SMS role so the user can choose Hyouka Messages as the default SMS application.
- The app reads real SMS conversations from Android's SMS provider.
- A normal tap opens the full selected conversation.
- Opening a conversation marks its messages as read.
- Long-pressing a conversation opens Delete / Cancel confirmation and deletes that conversation from the phone when confirmed.
- Select all confirms and deletes all SMS messages in one operation.
- Incoming SMS delivery is handled through Android's SMS_DELIVER broadcast when the app is the default SMS application.

Android's ROLE_SMS requires specific manifest components for SMS delivery and SENDTO/RESPOND_VIA_MESSAGE handling; the build workflow injects these components into the generated Android platform files.

## Privacy and permissions

SMS is sensitive user data. The app declares Android SMS permissions and requests them at runtime where the platform requires it. The app has no network data source and no runtime network dependency.

## Build

GitHub Actions generates the Android platform scaffold, configures the native SMS integration, runs Flutter analysis and widget tests, and builds the release APK.
