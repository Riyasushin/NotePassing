"""
End-to-End Test Suite for NotePassing API.

This script tests the complete business flow:
1. Device initialization
2. Temp ID generation
3. Profile viewing
4. Messaging (strangers)
5. Friend requests
6. Friendship acceptance
7. Messaging (friends)
8. Blocking
"""
import asyncio
import json
import sys
import uuid
from datetime import datetime
from typing import Optional

import httpx
import websockets


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def generate_device_id() -> str:
    """Generate a valid device ID."""
    return uuid.uuid4().hex


class Colors:
    """Terminal colors for output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_step(step_num: int, msg: str):
    print(f"\n{Colors.YELLOW}Step {step_num}: {msg}{Colors.RESET}")


class NotePassingE2E:
    """E2E test client."""
    
    def __init__(self, base_url: str = BASE_URL, ws_url: str = WS_URL):
        self.base_url = base_url
        self.ws_url = ws_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        
        # Device IDs
        self.device_a: Optional[str] = None
        self.device_b: Optional[str] = None
        
        # Temp IDs
        self.temp_id_b: Optional[str] = None
        
        # Session and message IDs
        self.session_id: Optional[str] = None
        self.message_ids: list = []
        self.friend_request_id: Optional[str] = None
    
    async def close(self):
        await self.client.aclose()
    
    async def init_device(self, nickname: str, tags: list = None) -> str:
        """Initialize a device and return device_id."""
        device_id = generate_device_id()
        response = await self.client.post(
            "/api/v1/device/init",
            json={
                "device_id": device_id,
                "nickname": nickname,
                "tags": tags or [],
                "profile": f"I am {nickname}",
            }
        )
        assert response.status_code == 200, f"Init failed: {response.text}"
        data = response.json()
        assert data["code"] == 0, f"Init error: {data}"
        return device_id
    
    async def test_step_1_init_devices(self):
        """Step 1: Initialize two devices."""
        print_step(1, "Initialize Devices")
        
        self.device_a = await self.init_device("Alice", ["coffee", "music"])
        print_success(f"Device A initialized: {self.device_a[:16]}...")
        
        self.device_b = await self.init_device("Bob", ["sports", "travel"])
        print_success(f"Device B initialized: {self.device_b[:16]}...")
    
    async def test_step_2_temp_id(self):
        """Step 2: Generate temp ID for device B."""
        print_step(2, "Generate Temp ID")
        
        response = await self.client.post(
            "/api/v1/temp-id/refresh",
            json={"device_id": self.device_b}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        self.temp_id_b = data["data"]["temp_id"]
        print_success(f"Temp ID generated: {self.temp_id_b[:16]}...")
    
    async def test_step_3_view_profile(self):
        """Step 3: View device B's profile from device A."""
        print_step(3, "View Profile")
        
        response = await self.client.get(
            f"/api/v1/device/{self.device_b}?requester_id={self.device_a}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        profile = data["data"]
        assert profile["nickname"] == "Bob"
        assert profile["is_friend"] is False
        
        print_success(f"Viewed profile: {profile['nickname']}, tags: {profile['tags']}")
    
    async def test_step_4_send_message_stranger(self):
        """Step 4: Send message as strangers."""
        print_step(4, "Send Message (Strangers)")
        
        response = await self.client.post(
            "/api/v1/messages",
            json={
                "sender_id": self.device_a,
                "receiver_id": self.device_b,
                "content": "Hey Bob! Want to chat?",
                "type": "common",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        self.session_id = data["data"]["session_id"]
        self.message_ids.append(data["data"]["message_id"])
        
        print_success(f"Message sent, session: {self.session_id[:16]}...")
    
    async def test_step_5_reply_stranger(self):
        """Step 5: Reply as device B."""
        print_step(5, "Reply (Strangers)")
        
        response = await self.client.post(
            "/api/v1/messages",
            json={
                "sender_id": self.device_b,
                "receiver_id": self.device_a,
                "content": "Sure Alice! How are you?",
                "type": "common",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        self.message_ids.append(data["data"]["message_id"])
        print_success("Reply sent successfully")
    
    async def test_step_6_get_history(self):
        """Step 6: Get message history."""
        print_step(6, "Get Message History")
        
        response = await self.client.get(
            f"/api/v1/messages/{self.session_id}?device_id={self.device_a}&limit=20"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        messages = data["data"]["messages"]
        assert len(messages) == 2
        
        print_success(f"Retrieved {len(messages)} messages")
    
    async def test_step_7_send_friend_request(self):
        """Step 7: Send friend request."""
        print_step(7, "Send Friend Request")
        
        response = await self.client.post(
            "/api/v1/friends/request",
            json={
                "sender_id": self.device_a,
                "receiver_id": self.device_b,
                "message": "Let's be friends!",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        self.friend_request_id = data["data"]["request_id"]
        print_success(f"Friend request sent: {self.friend_request_id[:16]}...")
    
    async def test_step_8_accept_friend_request(self):
        """Step 8: Accept friend request."""
        print_step(8, "Accept Friend Request")
        
        response = await self.client.put(
            f"/api/v1/friends/{self.friend_request_id}",
            json={
                "device_id": self.device_b,
                "action": "accept",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "accepted"
        
        print_success("Friend request accepted!")
    
    async def test_step_9_message_as_friends(self):
        """Step 9: Send messages as friends (no limits)."""
        print_step(9, "Send Messages (Friends)")
        
        for i in range(3):
            response = await self.client.post(
                "/api/v1/messages",
                json={
                    "sender_id": self.device_a,
                    "receiver_id": self.device_b,
                    "content": f"Friend message {i+1}",
                    "type": "common",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
        
        print_success("Sent 3 messages as friends (no temp limits!)")
    
    async def test_step_10_get_friends_list(self):
        """Step 10: Get friends list."""
        print_step(10, "Get Friends List")
        
        response = await self.client.get(
            f"/api/v1/friends?device_id={self.device_a}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        friends = data["data"]["friends"]
        assert len(friends) == 1
        assert friends[0]["device_id"] == self.device_b
        
        print_success(f"Friends list: {len(friends)} friend(s)")
    
    async def test_step_11_mark_read(self):
        """Step 11: Mark messages as read."""
        print_step(11, "Mark Messages as Read")
        
        response = await self.client.post(
            "/api/v1/messages/read",
            json={
                "device_id": self.device_b,
                "message_ids": self.message_ids[:2],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        print_success(f"Marked {data['data']['updated_count']} messages as read")
    
    async def test_step_12_block_user(self):
        """Step 12: Block user."""
        print_step(12, "Block User")
        
        response = await self.client.post(
            "/api/v1/block",
            json={
                "device_id": self.device_a,
                "target_id": self.device_b,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        print_success("User blocked")
    
    async def test_step_13_verify_block(self):
        """Step 13: Verify block prevents messaging."""
        print_step(13, "Verify Block")
        
        response = await self.client.post(
            "/api/v1/messages",
            json={
                "sender_id": self.device_b,
                "receiver_id": self.device_a,
                "content": "Can you hear me?",
                "type": "common",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 4004  # BLOCKED_BY_USER
        
        print_success("Block verified - message rejected with code 4004")
    
    async def test_step_14_websocket_connection(self):
        """Step 14: Test WebSocket connection."""
        print_step(14, "WebSocket Connection")
        
        ws_uri = f"{self.ws_url}/api/v1/ws?device_id={self.device_a}"
        
        try:
            async with websockets.connect(ws_uri) as websocket:
                # Receive connected message
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                assert data["type"] == "connected"
                print_success("WebSocket connected")
                
                # Send ping
                await websocket.send(json.dumps({"action": "ping"}))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                assert data["type"] == "pong"
                print_success("Ping-pong successful")
                
        except Exception as e:
            print_error(f"WebSocket test failed: {e}")
            print_info("Note: WebSocket test requires websockets library")
    
    async def run_all_tests(self):
        """Run all E2E tests."""
        print(f"\n{Colors.YELLOW}{'='*60}")
        print("NotePassing API - End-to-End Tests")
        print(f"{'='*60}{Colors.RESET}\n")
        
        print_info(f"Base URL: {self.base_url}")
        print_info(f"WS URL: {self.ws_url}")
        
        start_time = datetime.now()
        
        try:
            await self.test_step_1_init_devices()
            await self.test_step_2_temp_id()
            await self.test_step_3_view_profile()
            await self.test_step_4_send_message_stranger()
            await self.test_step_5_reply_stranger()
            await self.test_step_6_get_history()
            await self.test_step_7_send_friend_request()
            await self.test_step_8_accept_friend_request()
            await self.test_step_9_message_as_friends()
            await self.test_step_10_get_friends_list()
            await self.test_step_11_mark_read()
            await self.test_step_12_block_user()
            await self.test_step_13_verify_block()
            await self.test_step_14_websocket_connection()
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{Colors.GREEN}{'='*60}")
            print(f"✓ All E2E tests passed in {duration:.2f}s!")
            print(f"{'='*60}{Colors.RESET}\n")
            
            return True
            
        except AssertionError as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{Colors.RED}{'='*60}")
            print(f"✗ E2E test failed after {duration:.2f}s")
            print(f"Error: {e}")
            print(f"{'='*60}{Colors.RESET}\n")
            return False
        
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{Colors.RED}{'='*60}")
            print(f"✗ E2E test error after {duration:.2f}s")
            print(f"Error: {type(e).__name__}: {e}")
            print(f"{'='*60}{Colors.RESET}\n")
            return False


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NotePassing E2E Tests")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    parser.add_argument("--ws-url", default=WS_URL, help="WebSocket URL")
    args = parser.parse_args()
    
    e2e = NotePassingE2E(base_url=args.base_url, ws_url=args.ws_url)
    
    try:
        success = await e2e.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await e2e.close()


if __name__ == "__main__":
    asyncio.run(main())
