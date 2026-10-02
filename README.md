# رسائل

Minimal offline Flutter SMS app with a pure-black UI.

## Android identity

- App name: رسائل
- Application ID / package name: `com.messages.chat`

## SMS behavior

- Reads the device's real SMS conversations.
- On first launch, asks once to become the default SMS app.
- Opens a conversation with a single tap.
- Marks opened messages as read.
- Long-pressing a conversation offers delete or cancel.
- Select all starts a confirmation for deleting all SMS.
- Receives delivered SMS while it is the default SMS app and posts a notification for each newly received SMS when notifications are allowed.
- MMS UI is not implemented.
- Sending UI is not implemented yet.

The app uses no network connection for its message data.

## Build

GitHub Actions generates the Android platform project, configures the native SMS integration, applies the `com.messages.chat` package and `رسائل` app label, then builds the release APK.
