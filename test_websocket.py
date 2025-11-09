#!/usr/bin/env python3
"""
Quick WebSocket Test for Pipecat Agent
Tests if agent accepts WebSocket connections

Usage:
    python test_websocket.py
    python test_websocket.py --host 98.66.139.255
"""

import asyncio
import websockets
import sys

async def test_websocket(host="localhost", port=8000):
    url = f"ws://{host}:{port}/ws"
    print(f"Testing: {url}")
    
    try:
        async with websockets.connect(url, ping_interval=None) as ws:
            print(f"✅ CONNECTED to {url}")
            print("Sending test audio...")
            # Send 20ms of silence
            test_audio = b'\x00' * 320
            await ws.send(test_audio)
            print("✅ Audio sent")
            
            # Wait for response
            print("Waiting for response...")
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(response, bytes):
                    print(f"✅ GOT AUDIO RESPONSE: {len(response)} bytes")
                else:
                    print(f"✅ GOT MESSAGE: {response}")
            except asyncio.TimeoutError:
                print("⏱️ No response (might be waiting for voice)")
                
            print("\n✅ TEST PASSED - Agent is accepting connections!")
            return True
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    result = asyncio.run(test_websocket(host))
    sys.exit(0 if result else 1)
