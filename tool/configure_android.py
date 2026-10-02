from pathlib import Path
import re

ROOT = Path("android")
PACKAGE = "com.tomasthrawat.hyouka_messages"
SRC = ROOT / "app/src/main/kotlin" / Path(PACKAGE.replace(".", "/"))
SRC.mkdir(parents=True, exist_ok=True)

(SRC / "MainActivity.kt").write_text(
r'''package com.tomasthrawat.hyouka_messages

import android.Manifest
import android.app.Activity
import android.app.role.RoleManager
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Telephony
import android.provider.Telephony.Sms
import android.provider.Telephony.Sms.Intents
import io.flutter.embedding.android.FlutterActivity
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "hyouka.messages/sms"
        private const val ROLE_REQUEST = 4201
        private const val SMS_PERMISSIONS_REQUEST = 4202
        private const val NOTIFICATION_PERMISSION_REQUEST = 4203
        private const val PREFS = "hyouka_messages"
        private const val DEFAULT_PROMPT_SHOWN = "default_prompt_shown"
    }

    private var roleRequestInProgress = false

    override fun configureFlutterEngine(
        flutterEngine: io.flutter.embedding.engine.FlutterEngine
    ) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "isDefaultSmsApp" -> result.success(isDefaultSmsApp())
                "shouldPromptDefaultSmsApp" ->
                    result.success(!preferences().getBoolean(DEFAULT_PROMPT_SHOWN, false))
                "autoPromptDefaultSmsApp" -> autoPromptDefaultSmsApp(result)
                "requestDefaultSmsApp" -> requestDefaultSmsApp(result)
                "requestSmsPermissions" -> requestSmsPermissions(result)
                "requestNotificationPermission" -> requestNotificationPermission(result)
                "getConversations" -> queryConversations(result)

                "getThreadMessages" -> {
                    val threadId = call.argument<Int>("threadId")?.toLong()
                    if (threadId == null) {
                        result.error("INVALID_THREAD", "threadId is required.", null)
                    } else {
                        queryThreadMessages(threadId, result)
                    }
                }

                "deleteThread" -> {
                    val threadId = call.argument<Int>("threadId")?.toLong()
                    if (threadId == null) {
                        result.error("INVALID_THREAD", "threadId is required.", null)
                    } else {
                        deleteThread(threadId, result)
                    }
                }

                "deleteAllMessages" -> deleteAllMessages(result)
                else -> result.notImplemented()
            }
        }
    }

    private fun preferences() =
        getSharedPreferences(PREFS, MODE_PRIVATE)

    private fun isDefaultSmsApp(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            roleManager?.isRoleHeld(RoleManager.ROLE_SMS) == true
        } else {
            Telephony.Sms.getDefaultSmsPackage(this) == packageName
        }
    }

    private fun autoPromptDefaultSmsApp(result: MethodChannel.Result) {
        preferences().edit().putBoolean(DEFAULT_PROMPT_SHOWN, true).apply()
        requestDefaultSmsApp(result)
    }

    private fun requestDefaultSmsApp(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            if (roleManager == null ||
                !roleManager.isRoleAvailable(RoleManager.ROLE_SMS)
            ) {
                result.error(
                    "ROLE_UNAVAILABLE",
                    "The SMS role is not available on this device.",
                    null
                )
                return
            }

            if (roleManager.isRoleHeld(RoleManager.ROLE_SMS)) {
                result.success(true)
                return
            }

            if (roleRequestInProgress) {
                result.success(false)
                return
            }

            roleRequestInProgress = true
            startActivityForResult(
                roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS),
                ROLE_REQUEST
            )
            result.success(false)
        } else {
            val intent = Intent(Intents.ACTION_CHANGE_DEFAULT).apply {
                putExtra(Intents.EXTRA_PACKAGE_NAME, packageName)
            }
            startActivity(intent)
            result.success(false)
        }
    }

    override fun onActivityResult(
        requestCode: Int,
        resultCode: Int,
        data: Intent?
    ) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == ROLE_REQUEST) {
            roleRequestInProgress = false
        }
    }

    private fun requestSmsPermissions(result: MethodChannel.Result) {
        val required = mutableListOf(
            Manifest.permission.READ_SMS,
            Manifest.permission.SEND_SMS,
            Manifest.permission.RECEIVE_SMS
        )
        val missing = required.filter {
            checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isEmpty()) {
            result.success(true)
            return
        }

        requestPermissions(missing.toTypedArray(), SMS_PERMISSIONS_REQUEST)
        result.success(false)
    }

    private fun requestNotificationPermission(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            result.success(true)
            return
        }

        if (
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        ) {
            result.success(true)
            return
        }

        requestPermissions(
            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
            NOTIFICATION_PERMISSION_REQUEST
        )
        result.success(false)
    }

    private fun queryConversations(result: MethodChannel.Result) {
        Thread {
            try {
                val grouped = LinkedHashMap<Long, MutableMap<String, Any>>()
                val projection = arrayOf(
                    Sms.THREAD_ID,
                    Sms.ADDRESS,
                    Sms.BODY,
                    Sms.DATE,
                    Sms.READ
                )

                contentResolver.query(
                    Sms.CONTENT_URI,
                    projection,
                    null,
                    null,
                    Sms.DATE + " DESC"
                )?.use { cursor ->
                    val threadIndex = cursor.getColumnIndexOrThrow(Sms.THREAD_ID)
                    val addressIndex = cursor.getColumnIndexOrThrow(Sms.ADDRESS)
                    val bodyIndex = cursor.getColumnIndexOrThrow(Sms.BODY)
                    val dateIndex = cursor.getColumnIndexOrThrow(Sms.DATE)
                    val readIndex = cursor.getColumnIndexOrThrow(Sms.READ)

                    while (cursor.moveToNext()) {
                        val threadId = cursor.getLong(threadIndex)
                        val address = cursor.getString(addressIndex) ?: "Unknown"
                        val body = cursor.getString(bodyIndex) ?: ""
                        val date = cursor.getLong(dateIndex)
                        val unread = cursor.getInt(readIndex) == 0

                        if (!grouped.containsKey(threadId)) {
                            grouped[threadId] = mutableMapOf(
                                "threadId" to threadId.toInt(),
                                "address" to address,
                                "preview" to body,
                                "date" to date,
                                "messageCount" to 1,
                                "unread" to unread
                            )
                        } else {
                            val current = grouped.getValue(threadId)
                            current["messageCount"] =
                                (current["messageCount"] as Int) + 1
                            if (unread) current["unread"] = true
                        }
                    }
                }

                postSuccess(result, grouped.values.toList())
            } catch (security: SecurityException) {
                postError(
                    result,
                    "SMS_PERMISSION",
                    "SMS access was denied. Make Hyouka Messages the default SMS app and allow SMS permissions."
                )
            } catch (error: Exception) {
                postError(
                    result,
                    "SMS_READ",
                    error.message ?: "Unable to read SMS messages."
                )
            }
        }.start()
    }

    private fun queryThreadMessages(
        threadId: Long,
        result: MethodChannel.Result
    ) {
        Thread {
            try {
                val messages = ArrayList<Map<String, Any>>()
                val projection = arrayOf(
                    Sms._ID,
                    Sms.ADDRESS,
                    Sms.BODY,
                    Sms.DATE,
                    Sms.TYPE,
                    Sms.READ
                )

                contentResolver.query(
                    Sms.CONTENT_URI,
                    projection,
                    Sms.THREAD_ID + " = ?",
                    arrayOf(threadId.toString()),
                    Sms.DATE + " ASC"
                )?.use { cursor ->
                    val idIndex = cursor.getColumnIndexOrThrow(Sms._ID)
                    val addressIndex = cursor.getColumnIndexOrThrow(Sms.ADDRESS)
                    val bodyIndex = cursor.getColumnIndexOrThrow(Sms.BODY)
                    val dateIndex = cursor.getColumnIndexOrThrow(Sms.DATE)
                    val typeIndex = cursor.getColumnIndexOrThrow(Sms.TYPE)
                    val readIndex = cursor.getColumnIndexOrThrow(Sms.READ)

                    while (cursor.moveToNext()) {
                        messages += mapOf(
                            "id" to cursor.getLong(idIndex).toInt(),
                            "address" to (cursor.getString(addressIndex) ?: "Unknown"),
                            "body" to (cursor.getString(bodyIndex) ?: ""),
                            "date" to cursor.getLong(dateIndex),
                            "type" to cursor.getInt(typeIndex),
                            "read" to (cursor.getInt(readIndex) != 0)
                        )
                    }
                }

                val values = ContentValues().apply {
                    put(Sms.READ, 1)
                    put(Sms.SEEN, 1)
                }
                contentResolver.update(
                    Sms.CONTENT_URI,
                    values,
                    Sms.THREAD_ID + " = ?",
                    arrayOf(threadId.toString())
                )

                postSuccess(result, messages)
            } catch (security: SecurityException) {
                postError(result, "SMS_PERMISSION", "SMS access was denied.")
            } catch (error: Exception) {
                postError(
                    result,
                    "SMS_READ",
                    error.message ?: "Unable to open the conversation."
                )
            }
        }.start()
    }

    private fun deleteThread(
        threadId: Long,
        result: MethodChannel.Result
    ) {
        Thread {
            try {
                contentResolver.delete(
                    Sms.CONTENT_URI,
                    Sms.THREAD_ID + " = ?",
                    arrayOf(threadId.toString())
                )
                postSuccess(result, true)
            } catch (security: SecurityException) {
                postError(
                    result,
                    "SMS_WRITE",
                    "Only the default SMS app can delete SMS messages."
                )
            } catch (error: Exception) {
                postError(
                    result,
                    "SMS_DELETE",
                    error.message ?: "Unable to delete the conversation."
                )
            }
        }.start()
    }

    private fun deleteAllMessages(result: MethodChannel.Result) {
        Thread {
            try {
                contentResolver.delete(Sms.CONTENT_URI, null, null)
                postSuccess(result, true)
            } catch (security: SecurityException) {
                postError(
                    result,
                    "SMS_WRITE",
                    "Only the default SMS app can delete SMS messages."
                )
            } catch (error: Exception) {
                postError(
                    result,
                    "SMS_DELETE",
                    error.message ?: "Unable to delete SMS messages."
                )
            }
        }.start()
    }

    private fun postSuccess(
        result: MethodChannel.Result,
        value: Any?
    ) {
        Handler(Looper.getMainLooper()).post {
            result.success(value)
        }
    }

    private fun postError(
        result: MethodChannel.Result,
        code: String,
        message: String
    ) {
        Handler(Looper.getMainLooper()).post {
            result.error(code, message, null)
        }
    }
}
''',
encoding="utf-8"
)

(SRC / "SmsNotificationHelper.kt").write_text('package com.tomasthrawat.hyouka_messages\n\nimport android.Manifest\nimport android.app.Notification\nimport android.app.NotificationChannel\nimport android.app.NotificationManager\nimport android.app.PendingIntent\nimport android.content.Context\nimport android.content.Intent\nimport android.content.pm.PackageManager\nimport android.graphics.Color\nimport android.os.Build\nimport android.widget.RemoteViews\n\nobject SmsNotificationHelper {\n    private const val CHANNEL_ID = "incoming_messages"\n    private const val CHANNEL_NAME = "Messages"\n    private const val CHANNEL_DESCRIPTION =\n        "Notifications for newly received SMS messages."\n\n    fun showIncomingMessage(\n        context: Context,\n        address: String,\n        body: String\n    ) {\n        if (\n            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&\n            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=\n                PackageManager.PERMISSION_GRANTED\n        ) {\n            return\n        }\n\n        val manager = context.getSystemService(\n            Context.NOTIFICATION_SERVICE\n        ) as NotificationManager\n\n        createChannel(manager)\n\n        val launchIntent = Intent(context, MainActivity::class.java).apply {\n            flags =\n                Intent.FLAG_ACTIVITY_NEW_TASK or\n                    Intent.FLAG_ACTIVITY_CLEAR_TOP or\n                    Intent.FLAG_ACTIVITY_SINGLE_TOP\n        }\n\n        var pendingIntentFlags = PendingIntent.FLAG_UPDATE_CURRENT\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {\n            pendingIntentFlags =\n                pendingIntentFlags or PendingIntent.FLAG_IMMUTABLE\n        }\n\n        val pendingIntent = PendingIntent.getActivity(\n            context,\n            0,\n            launchIntent,\n            pendingIntentFlags\n        )\n\n        val customView = RemoteViews(\n            context.packageName,\n            R.layout.notification_message\n        ).apply {\n            setTextViewText(R.id.notification_sender, address)\n            setTextViewText(R.id.notification_body, body)\n        }\n\n        val builder =\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {\n                Notification.Builder(context, CHANNEL_ID)\n            } else {\n                Notification.Builder(context)\n            }\n\n        builder\n            .setSmallIcon(R.drawable.ic_stat_message)\n            .setContentTitle(address)\n            .setContentText(body)\n            .setStyle(Notification.BigTextStyle().bigText(body))\n            .setColor(Color.BLACK)\n            .setAutoCancel(true)\n            .setCategory(Notification.CATEGORY_MESSAGE)\n            .setVisibility(Notification.VISIBILITY_PRIVATE)\n            .setContentIntent(pendingIntent)\n\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {\n            builder.setCustomContentView(customView)\n            builder.setCustomBigContentView(customView)\n        }\n\n        val notificationId =\n            (System.currentTimeMillis() and 0x7fffffff).toInt()\n        manager.notify(notificationId, builder.build())\n    }\n\n    private fun createChannel(manager: NotificationManager) {\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return\n\n        val channel = NotificationChannel(\n            CHANNEL_ID,\n            CHANNEL_NAME,\n            NotificationManager.IMPORTANCE_HIGH\n        ).apply {\n            description = CHANNEL_DESCRIPTION\n            enableLights(false)\n            lightColor = Color.BLACK\n        }\n\n        manager.createNotificationChannel(channel)\n    }\n}\n', encoding="utf-8")

(SRC / "SmsReceiver.kt").write_text(
r'''package com.tomasthrawat.hyouka_messages

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.provider.Telephony.Sms
import android.provider.Telephony.Sms.Intents

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intents.SMS_DELIVER_ACTION) return

        val messages = Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) {
            resultCode = Activity.RESULT_OK
            return
        }

        val body = messages.joinToString(separator = "") {
            it.messageBody ?: ""
        }
        val address = messages.firstOrNull()?.displayOriginatingAddress
            ?: messages.firstOrNull()?.originatingAddress
            ?: "Unknown"

        val values = ContentValues().apply {
            put(Sms.ADDRESS, address)
            put(Sms.BODY, body)
            put(Sms.DATE, System.currentTimeMillis())
            put(Sms.READ, 0)
            put(Sms.SEEN, 0)
            put(Sms.TYPE, Sms.MESSAGE_TYPE_INBOX)

            val subscriptionId = intent.getIntExtra(
                "subscription",
                Int.MIN_VALUE
            )
            if (subscriptionId != Int.MIN_VALUE) {
                put(Sms.SUBSCRIPTION_ID, subscriptionId)
            }
        }

        try {
            val inserted = context.contentResolver.insert(
                Sms.Inbox.CONTENT_URI,
                values
            )
            if (inserted != null) {
                SmsNotificationHelper.showIncomingMessage(
                    context = context,
                    address = address,
                    body = body
                )
            }
        } finally {
            resultCode = Activity.RESULT_OK
        }
    }
}
''',
encoding="utf-8"
)

(SRC / "WapPushReceiver.kt").write_text(
r'''package com.tomasthrawat.hyouka_messages

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class WapPushReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // MMS is intentionally not implemented in this minimal build.
    }
}
''',
encoding="utf-8"
)

(SRC / "RespondViaMessageService.kt").write_text(
r'''package com.tomasthrawat.hyouka_messages

import android.app.Service
import android.content.Intent
import android.os.IBinder

class RespondViaMessageService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        stopSelf(startId)
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
''',
encoding="utf-8"
)

# Generate pure-black notification resources with the native SMS integration.
RES = ROOT / "app/src/main/res"
(RES / "layout").mkdir(parents=True, exist_ok=True)
(RES / "drawable").mkdir(parents=True, exist_ok=True)

(RES / "layout/notification_message.xml").write_text('<?xml version="1.0" encoding="utf-8"?>\n<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"\n    android:layout_width="match_parent"\n    android:layout_height="wrap_content"\n    android:minHeight="64dp"\n    android:orientation="vertical"\n    android:background="#000000"\n    android:paddingStart="16dp"\n    android:paddingTop="12dp"\n    android:paddingEnd="16dp"\n    android:paddingBottom="12dp">\n\n    <TextView\n        android:id="@+id/notification_sender"\n        android:layout_width="match_parent"\n        android:layout_height="wrap_content"\n        android:ellipsize="end"\n        android:maxLines="1"\n        android:textColor="#FFFFFFFF"\n        android:textSize="16sp"\n        android:textStyle="bold" />\n\n    <TextView\n        android:id="@+id/notification_body"\n        android:layout_width="match_parent"\n        android:layout_height="wrap_content"\n        android:layout_marginTop="4dp"\n        android:ellipsize="end"\n        android:maxLines="3"\n        android:textColor="#FFBDBDBD"\n        android:textSize="14sp" />\n</LinearLayout>\n', encoding="utf-8")

(RES / "drawable/ic_stat_message.xml").write_text('<?xml version="1.0" encoding="utf-8"?>\n<vector xmlns:android="http://schemas.android.com/apk/res/android"\n    android:width="24dp"\n    android:height="24dp"\n    android:viewportWidth="24"\n    android:viewportHeight="24">\n    <path\n        android:fillColor="#FFFFFFFF"\n        android:pathData="M20,2H4C2.9,2 2,2.9 2,4V18C2,19.1 2.9,20 4,20H8L12,24L16,20H20C21.1,20 22,19.1 22,18V4C22,2.9 21.1,2 20,2ZM7,10H17V12H7V10ZM7,14H14V16H7V14ZM7,6H17V8H7V6Z" />\n</vector>\n', encoding="utf-8")

manifest = ROOT / "app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")

permission_block = """
    <uses-permission android:name="android.permission.READ_SMS" />
    <uses-permission android:name="android.permission.RECEIVE_SMS" />
    <uses-permission android:name="android.permission.SEND_SMS" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
"""

manifest_match = re.search(r"<manifest\b[^>]*>", text)
if not manifest_match:
    raise RuntimeError("Generated AndroidManifest.xml has no manifest element")

missing_permissions = [
    permission
    for permission in (
        "android.permission.READ_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.SEND_SMS",
        "android.permission.POST_NOTIFICATIONS",
    )
    if f'android:name="{permission}"' not in text
]
if missing_permissions:
    declarations = "".join(
        f'    <uses-permission android:name="{permission}" />\n'
        for permission in missing_permissions
    )
    insert_at = manifest_match.end()
    text = text[:insert_at] + "\n" + declarations + text[insert_at:]

activity_filters = """
            <intent-filter>
                <action android:name="android.intent.action.SENDTO" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.APP_MESSAGING" />
                <data android:scheme="sms" />
                <data android:scheme="smsto" />
                <data android:scheme="mms" />
                <data android:scheme="mmsto" />
            </intent-filter>
"""

if 'android.intent.action.SENDTO' not in text:
    marker = '</activity>'
    pos = text.find(marker, text.find('android:name=".MainActivity"'))
    if pos == -1:
        raise RuntimeError("MainActivity activity not found in generated manifest")
    text = text[:pos] + activity_filters + text[pos:]

application_components = """
        <service
            android:name=".RespondViaMessageService"
            android:exported="true"
            android:permission="android.permission.SEND_RESPOND_VIA_MESSAGE">
            <intent-filter>
                <action android:name="android.intent.action.RESPOND_VIA_MESSAGE" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:scheme="smsto" />
            </intent-filter>
        </service>

        <receiver
            android:name=".SmsReceiver"
            android:exported="true"
            android:permission="android.permission.BROADCAST_SMS">
            <intent-filter>
                <action android:name="android.provider.Telephony.SMS_DELIVER" />
            </intent-filter>
        </receiver>

        <receiver
            android:name=".WapPushReceiver"
            android:exported="true"
            android:permission="android.permission.BROADCAST_WAP_PUSH">
            <intent-filter>
                <action android:name="android.provider.Telephony.WAP_PUSH_DELIVER" />
                <data android:mimeType="application/vnd.wap.mms-message" />
            </intent-filter>
        </receiver>
"""

if 'android:name=".SmsReceiver"' not in text:
    text = text.replace('</application>', application_components + '</application>', 1)

manifest.write_text(text, encoding="utf-8")
