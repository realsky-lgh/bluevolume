import sys
import time
import json
import socket
import threading
import unittest

from server.pc_server import AudioController, SystemController, start_tcp_server, get_os_info

class TestServerProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio_ctrl = AudioController()
        cls.port = 18888
        cls.server_thread = threading.Thread(
            target=start_tcp_server,
            args=(cls.audio_ctrl, cls.port),
            daemon=True
        )
        cls.server_thread.start()
        time.sleep(0.5)

    def test_get_os_info(self):
        info = get_os_info()
        self.assertIn(info["os_type"], ["windows", "macos", "linux", "unknown"])
        self.assertTrue(len(info["os_name"]) > 0)
        print("Detected OS Info:", info)

    def test_socket_communication(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))

        # 1. 验证连接后收到的初始 SYSTEM_INFO
        initial_data = client.recv(1024).decode("utf-8")
        first_line = initial_data.strip().split("\n")[0]
        msg = json.loads(first_line)
        self.assertEqual(msg["type"], "SYSTEM_INFO")
        self.assertIn("os_type", msg)
        self.assertIn("volume", msg)
        print("Received Handshake:", msg)

        # 2. 验证 SET_VOLUME 指令
        test_vol = 37
        client.sendall(json.dumps({"type": "SET_VOLUME", "volume": test_vol}).encode("utf-8") + b"\n")
        reply = client.recv(1024).decode("utf-8").strip().split("\n")[0]
        reply_msg = json.loads(reply)
        self.assertEqual(reply_msg["type"], "VOLUME_CHANGED")
        self.assertEqual(reply_msg["volume"], test_vol)
        print("Received Volume Change Ack:", reply_msg)

        # 3. 验证 GET_SYSTEM_INFO
        client.sendall(json.dumps({"type": "GET_SYSTEM_INFO"}).encode("utf-8") + b"\n")
        reply = client.recv(1024).decode("utf-8").strip().split("\n")[0]
        reply_msg = json.loads(reply)
        self.assertEqual(reply_msg["type"], "SYSTEM_INFO")

        client.close()

if __name__ == "__main__":
    unittest.main()
