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
        return try {
            gson.fromJson(jsonStr, ProtocolMessage::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun makeGetSystemInfo(): String = toJson(ProtocolMessage(type = "GET_SYSTEM_INFO"))

    fun makeSetVolume(volume: Int): String = toJson(
        ProtocolMessage(type = "SET_VOLUME", volume = volume.coerceIn(0, 100))
    )

    fun makeShutdown(): String = toJson(ProtocolMessage(type = "SHUTDOWN"))
}
