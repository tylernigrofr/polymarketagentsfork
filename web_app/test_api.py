#!/usr/bin/env python3
"""
Simple test script to check Polymarket Gamma API
"""

import httpx
import asyncio

async def test_api():
    print("Testing Polymarket Gamma API...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with correct parameters from gamma.py
            params = {
                "active": True,
                "closed": False,
                "archived": False,
                "limit": 5
            }

            print(f"Using params: {params}")
            response = await client.get("https://gamma-api.polymarket.com/markets", params=params)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Total markets returned: {len(data)}")

                if data:
                    print("\nAll markets:")
                    for i, market in enumerate(data):
                        print(f"{i+1}. ID: {market.get('id')}")
                        print(f"   Question: {market.get('question', '')[:80]}...")
                        print(f"   Active: {market.get('active')}, Closed: {market.get('closed')}")
                        print(f"   End Date: {market.get('endDate')}")
                        print(f"   Created: {market.get('createdAt', '')[:10] if market.get('createdAt') else 'N/A'}")
                        print()
                else:
                    print("No markets returned with active filter")

                    # Try without parameters
                    print("\nTrying without parameters...")
                    response2 = await client.get("https://gamma-api.polymarket.com/markets")
                    if response2.status_code == 200:
                        data2 = response2.json()
                        print(f"Total markets without params: {len(data2)}")
                        if data2:
                            market = data2[0]
                            print(f"First market: {market.get('question', '')[:100]}...")
                            print(f"Active: {market.get('active')}")
            else:
                print(f"API Error: {response.text}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

async def test_web_app():
    """Test the web app endpoints"""
    print("\n" + "="*50)
    print("Testing Web App Endpoints")
    print("="*50)

    try:
        # Import the web app
        import sys
        import os
        sys.path.append('.')

        # Set up minimal environment
        os.environ['OPENROUTER_API_KEY'] = 'test-key'

        import standalone_main

        # Test markets endpoint
        print("Testing /markets endpoint...")
        from fastapi.testclient import TestClient
        client = TestClient(standalone_main.app)

        response = client.get("/markets?limit=3")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Markets returned: {len(data)}")

            if data:
                market = data[0]
                print(f"First market: {market['question'][:60]}...")
                print(f"Active: {market['active']}")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Web app test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())
    asyncio.run(test_web_app())