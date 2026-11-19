package com.example.bluevolume.bluetooth

import com.google.gson.Gson

data class ProtocolMessage(
    val type: String,
    val os_type: String? = null,
    val os_name: String? = null,
    val hostname: String? = null,
    val volume: Int? = null,
    val status: String? = null
)

object Protocol {
    private val gson = Gson()

    fun toJson(msg: ProtocolMessage): String = gson.toJson(msg) + "\n"

    fun parse(jsonStr: String): ProtocolMessage? {
        val trimmed = jsonStr.trim()
        return try {
            // 优先直接解析
            gson.fromJson(trimmed, ProtocolMessage::class.java)
        } catch (e: Exception) {
            // 容错处理：若存在多余字符或多行粘包，截取首个完整的 { ... }
            try {
                val start = trimmed.indexOf('{')
                val end = trimmed.lastIndexOf('}')
                if (start in 0 until end) {
                    val sub = trimmed.substring(start, end + 1)
                    gson.fromJson(sub, ProtocolMessage::class.java)
                } else null
            } catch (_: Exception) {
                null
            }
        }
    }

    fun makeGetSystemInfo(): String = toJson(ProtocolMessage(type = "GET_SYSTEM_INFO"))

    fun makeSetVolume(volume: Int): String = toJson(
        ProtocolMessage(type = "SET_VOLUME", volume = volume.coerceIn(0, 100))
    )

    fun makeShutdown(): String = toJson(ProtocolMessage(type = "SHUTDOWN"))
}
