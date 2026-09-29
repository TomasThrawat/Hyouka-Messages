from pathlib import Path

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
        val required = arrayOf(
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
),
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
            context.contentResolver.insert(Sms.Inbox.CONTENT_URI, values)
        } finally {
            resultCode = Activity.RESULT_OK
        }
    }
}
''',
encoding="utf-8"
),
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
),
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

manifest = ROOT / "app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")

permission_block = """
    <uses-permission android:name="android.permission.READ_SMS" />
    <uses-permission android:name="android.permission.RECEIVE_SMS" />
    <uses-permission android:name="android.permission.SEND_SMS" />
"""

if 'android.permission.READ_SMS' not in text:
    first_close = text.find('>')
    text = text[:first_close + 1] + permission_block + text[first_close + 1:]

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
    text = text.replace('</application>', application_components + '
    </application>', 1)

manifest.write_text(text, encoding="utf-8")
